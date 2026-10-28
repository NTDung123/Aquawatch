'use strict';

// Clock, DOM and detections below are test doubles for causal UI behavior, not AI quality evidence.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'web', 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(root, 'web', 'index.html'), 'utf8');
const ids = new Set([...source.matchAll(/\$\('([^']+)'\)/g)].map((match) => match[1]));
for (const id of ids) assert.ok(html.includes(`id="${id}"`), `Missing HTML element #${id}`);

const elements = new Map();
const canvasContext = new Proxy({ measureText: (text) => ({ width: text.length * 5 }) }, { get: (target, key) => target[key] || (() => {}) });
function element(id) {
  if (!elements.has(id)) {
    const listeners = new Map();
    elements.set(id, {
      id, value: ({ 'sample-fps': '5', 'confidence': '.4', 'analysis-mode': 'realtime', 'camera-mode': 'fixed', 'environment': 'pool', 'library-camera': 'all', 'library-role': 'all' })[id] || '',
      checked: false, hidden: false, disabled: false, style: {}, innerHTML: '', textContent: '',
      classList: { add() {}, remove() {}, toggle() {} },
      addEventListener(name, callback) { listeners.set(name, callback); },
      emit(name, event = {}) { listeners.get(name)?.(event); },
      setAttribute() {}, appendChild() {}, scrollIntoView() {}, focus() {},
      getContext: () => canvasContext, clientWidth: 640, clientHeight: 360,
      getBoundingClientRect: () => ({ left: 0, top: 0, width: 640, height: 360 })
    });
  }
  return elements.get(id);
}
const video = element('video');
Object.assign(video, {
  currentTime: 0, duration: 20, videoWidth: 640, videoHeight: 360, paused: true, playCalls: 0,
  pause() { const wasPlaying = !this.paused; this.paused = true; if (wasPlaying) this.emit('pause'); },
  play() { this.playCalls += 1; this.paused = false; this.emit('play'); return Promise.resolve(); },
  load() {}, removeAttribute() {}
});
const sandbox = vm.createContext({
  document: { getElementById: element, querySelector: () => element('upload-zone'), querySelectorAll: () => [], createElement: () => element(`marker-${Math.random()}`) },
  window: { devicePixelRatio: 1, isSecureContext: false, addEventListener() {} }, navigator: {}, URL, console,
  requestAnimationFrame() {}, setTimeout() { return 1; }, clearTimeout() {}, setInterval() {},
  fetch: async (url) => ({ ok: true, json: async () => url === '/api/status' ? { model: { ready: true, name: 'transport test', device: 'test' } } : [] })
});
vm.runInContext(source, sandbox);
const run = (code) => vm.runInContext(code, sandbox);

async function main() {
  await new Promise(setImmediate);
  run("state.analysis={samples:[{time:1,detections:[]},{time:1.2,detections:[]}],events:[]}; state.job={config:{sample_fps:5,mode:'batch'},status:'completed'};");
  assert.equal(run('sampleAt(.99)'), null, 'Future samples cannot supply a bounding box');
  assert.equal(run('sampleAt(1.19).sample.time'), 1);
  assert.equal(run('sampleAt(1.2).sample.time'), 1.2);
  assert.equal(run('sampleAt(2.1)'), null, 'Stale bounding boxes expire');
  assert.equal(run('confidenceText(null)'), 'không xác định');

  run("state.job={id:'stream',status:'running',config:{mode:'realtime',sample_fps:5}};state.analysis={partial:true,processed_until:2,samples:[{time:1,detections:[]},{time:2,detections:[]}],events:[]};state.playbackIntent=true;state.bufferPaused=false;");
  video.currentTime = 3;
  video.paused = false;
  run('enforceBuffer()');
  assert.equal(video.currentTime, 2, 'Playback cannot pass the produced watermark');
  assert.equal(video.paused, true);
  assert.equal(run('state.playbackIntent'), true, 'Buffering preserves the user play intent');

  video.currentTime = 19;
  video.emit('seeking');
  assert.equal(video.currentTime, 2, 'Native seek ahead is clamped to analyzed video');
  video.emit('seeked');

  run("state.analysis.processed_until=5;state.analysis.samples.push({time:5,detections:[]});state.bufferPaused=true;state.playbackIntent=false;");
  video.currentTime = 1;
  const before = video.playCalls;
  run('enforceBuffer()');
  assert.equal(video.playCalls, before, 'New chunks do not resume a user-paused video');
  run('state.playbackIntent=true;enforceBuffer()');
  await new Promise(setImmediate);
  assert.equal(video.playCalls, before + 1, 'New chunks resume only a wanted buffered playback');
  assert.equal(video.paused, false);

  run("state.job.status='cancelled';state.analysis.partial=true;state.analysis.processed_until=2;state.analysis.samples=[{time:2,detections:[]}];state.playbackIntent=true;");
  video.currentTime = 3;
  run('enforceBuffer()');
  assert.equal(video.currentTime, 2, 'Cancelled partial jobs keep their final frontier');
  assert.equal(run('state.playbackIntent'), false);
  run("state.job.status='completed';state.analysis.partial=false;");
  assert.equal(run('hasFrontier()'), false, 'Complete jobs allow full replay');

  run("state.job={id:'causal',status:'running',config:{mode:'realtime',sample_fps:5}};state.analysis={partial:true,processed_until:10,samples:[{time:1,motion_known:true,level:2,detections:[{track_id:1,box:[.2,.2,.3,.4],label:'drowning',confidence:.8,level:2,reasons:[]}]}],events:[{id:'visible',track_id:1,start:1,end:8,level:2,confidence:.8,reasons:[]},{id:'future',track_id:2,start:5,end:8,level:3,confidence:.8,reasons:[]}]};state.notified.clear();state.eventSignature='';state.bufferPaused=false;state.seeking=false;");
  video.currentTime = 1;
  video.paused = false;
  element('review-mode').checked = true;
  run('renderFrame(true)');
  assert.ok(!element('event-list').innerHTML.includes('data-ack="future"'), 'Running monitoring hides future event IDs even if review was checked');
  assert.equal(run('state.notified.size'), 1);
  run('state.analysis.events[0].end=9;renderFrame(true)');
  assert.equal(run('state.notified.size'), 1, 'Partial snapshot refresh does not duplicate the alarm');
  assert.equal(run("safeLink('javascript:alert(1)')"), '');
  assert.equal(run("videoRole({category:'staged_passive_float',nature:'instructional_drill'})"), 'positive', 'Passive-float drills remain findable in the risk/rescue context group');
  assert.equal(run("videoRole({category:'normal_swimming'})"), 'negative');
  assert.equal(run("videoRole({category:'negative_background'})"), 'negative');
  assert.equal(run("searchText('Cứu hộ · Đuối nước')"), 'cuu ho · duoi nuoc', 'Vietnamese library search supports unaccented input');
  assert.ok(run("cameraLabel({camera_mode:'fixed',camera_type:'visually_stable_shore_view_mount_unknown'})").includes('chưa xác minh vị trí lắp'), 'Stable framing does not claim a confirmed camera installation');
  for (const phase of ['submitting', 'uploading']) {
    run(`state.job=null;state.submitting=false;state.uploading=false;state.${phase}=true;state.videos=[{id:'locked',name:'Current video',url:'/current.mp4',duration:5},{id:'other',name:'Other video',url:'/other.mp4',duration:5}];state.selected=state.videos[0];`);
    element('library-search').value = '';
    run('renderLibrary()');
    let picks = [...element('library-grid').innerHTML.matchAll(/<button class="library-pick"[^>]*>/g)];
    assert.equal(picks.length, 2);
    assert.ok(picks.every((match) => match[0].includes(' disabled')), `${phase}: initial library picks stay disabled`);
    element('library-search').value = 'Other';
    element('library-search').emit('input');
    picks = [...element('library-grid').innerHTML.matchAll(/<button class="library-pick"[^>]*>/g)];
    assert.equal(picks.length, 1);
    assert.ok(picks[0][0].includes(' disabled'), `${phase}: filtering cannot recreate enabled library picks`);
    run('selectVideo(state.videos[1])');
    assert.equal(run('state.selected.id'), 'locked', `${phase}: direct selection cannot orphan an in-flight upload/job`);
    assert.equal(run('state.generation'), 0, `${phase}: blocked selection does not change the request generation`);
  }
  console.log(`Frontend causal playback checks passed; ${ids.size} HTML element bindings verified.`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
