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
      emit(name, event = {}) { return listeners.get(name)?.(event); },
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
let fetchHandler = async (url) => ({ ok: true, json: async () => url === '/api/status' ? { model: { ready: true, loaded: true, name: 'transport test', device: 'test' } } : [] });
const timers = [];
const clock = { now: 10000 };
class TestDate extends Date { static now() { return clock.now; } }
const audioBehavior = { initialState: 'suspended', rejectResume: false, blockedResume: false };
const audioContexts = [], oscillators = [], gains = [], storedPreferences = new Map();
class TestAudioContext {
  constructor() { this.state = audioBehavior.initialState; this.destination = {}; this.resumeCalls = 0; audioContexts.push(this); }
  get currentTime() { return clock.now / 1000; }
  setState(state) { this.state = state; this.onstatechange?.(); }
  resume() {
    this.resumeCalls += 1;
    if (audioBehavior.rejectResume) return Promise.reject(new Error('Gesture required'));
    if (!audioBehavior.blockedResume) this.setState('running');
    return Promise.resolve();
  }
  createOscillator() {
    const oscillator = { frequency: { setValueAtTime() {}, linearRampToValueAtTime() {} },
      starts: [], stops: [], connected: false, connect() { this.connected = true; }, disconnect() { this.connected = false; },
      start(time) { this.starts.push(time); }, stop(time) { this.stops.push(time); } };
    oscillators.push(oscillator); return oscillator;
  }
  createGain() {
    const gain = { gain: { setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {}, cancelScheduledValues() {} },
      connected: false, connect() { this.connected = true; }, disconnect() { this.connected = false; } };
    gains.push(gain); return gain;
  }
}
class TestFormData { constructor() { this.values = new Map(); } append(key,value) { this.values.set(key,value); } }
const sandbox = vm.createContext({
  document: { getElementById: element, querySelector: () => element('upload-zone'), querySelectorAll: () => [], createElement: () => element(`marker-${Math.random()}`) },
  window: { devicePixelRatio: 1, isSecureContext: false, addEventListener() {}, AudioContext: TestAudioContext,
    localStorage: { getItem: (key) => storedPreferences.get(key) ?? null, setItem: (key,value) => storedPreferences.set(key,value) } }, navigator: {}, URL, console, Date: TestDate,
  requestAnimationFrame() {}, setTimeout(callback, milliseconds) { timers.push({callback,milliseconds}); return timers.length; }, clearTimeout() {}, setInterval() {}, FormData: TestFormData,
  fetch: (url, options) => fetchHandler(url, options)
});
vm.runInContext(source, sandbox);
const run = (code) => vm.runInContext(code, sandbox);

const response = (body, status = 200) => ({ok: status >= 200 && status < 300, status, json: async () => body});
const flush = async () => { for (let i = 0; i < 12; i++) await new Promise(setImmediate); };
async function until(predicate) { for (let i = 0; i < 30 && !predicate(); i++) await flush(); assert.ok(predicate(), 'Expected asynchronous checkpoint'); }
function fireDelay(milliseconds) { const at = timers.findIndex((entry) => entry.milliseconds === milliseconds); assert.ok(at >= 0, `Expected ${milliseconds}ms wait`); const [entry] = timers.splice(at,1); entry.callback(); }
function bannerLayoutTest() {
  const stack = [], voidTags = new Set(['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']);
  let ancestors = null;
  for (const match of html.matchAll(/<\/?([a-z][a-z0-9:-]*)\b[^>]*>/gi)) {
    const tag = match[1].toLowerCase(), token = match[0];
    if (token.startsWith('</')) { const at = stack.map((item) => item.tag).lastIndexOf(tag); if (at >= 0) stack.length = at; continue; }
    const item = { tag, id: token.match(/\bid="([^"]*)"/)?.[1], classes: token.match(/\bclass="([^"]*)"/)?.[1]?.split(/\s+/) || [] };
    if (item.id === 'alert-banner') ancestors = [...stack];
    if (!voidTags.has(tag) && !token.endsWith('/>')) stack.push(item);
  }
  assert.ok(ancestors?.some((item) => item.classes.includes('monitor-panel')), 'Risk banner belongs to the monitor panel');
  assert.ok(!ancestors.some((item) => item.id === 'video-stage' || item.id === 'video-wrap'), 'Risk banner is outside the video frame');
}
async function audioTests() {
  function activeAlarm() {
    run("stopAlarms();state.audio=null;state.audioActivation++;state.audioEnabled=true;state.audioMutedByUser=false;state.audioNeedsReplay=false;state.audioBlocked=false;state.audioError='';state.audioDeliverySerial=0;state.audioLastByEvent.clear();state.notified.clear();state.acked.clear();state.lastAlarmAt=-Infinity;state.lastAlarmLevel=0;state.volume=.25;state.seeking=false;state.sampleIndex=-1;state.job={id:'audio',status:'completed',config:{mode:'batch',sample_fps:5}};state.analysis={samples:[{time:1,motion_known:true,detections:[{track_id:1,box:[.2,.2,.3,.4],label:'drowning',confidence:.8,level:2,reasons:[]}]}],events:[{id:'danger',track_id:1,start:1,end:8,level:2,reasons:[]},{id:'future',track_id:2,start:5,end:8,level:3,reasons:[]}]};");
    Object.assign(video,{currentTime:1,paused:false,ended:false,seeking:false,readyState:4});
    Object.assign(audioBehavior,{initialState:'suspended',rejectResume:false,blockedResume:false});
    clock.now += 10000;
  }
  activeAlarm();
  const before = oscillators.length;
  assert.equal(run('processCurrentAlarms()'),false);
  assert.equal(run('state.notified.size'),0,'A blocked or unarmed sound is not recorded as delivered');
  await run('enableAudio({explicit:true,announceCurrent:true})');
  assert.equal(run('state.audioDeliverySerial'),1,'Enabling sound announces the active event');
  assert.equal(oscillators.length,before+3,'Level 2 schedules three audible oscillator pulses');
  assert.ok(oscillators.slice(-3).every((item)=>item.starts.length===1 && item.connected),'Every pulse is started and connected');
  assert.ok(gains.slice(-3).every((item)=>item.connected),'Sound output is connected to the audio destination');
  run('processCurrentAlarms();renderFrame(true);processCurrentAlarms()');
  assert.equal(run('state.audioDeliverySerial'),1,'Polling does not duplicate a just-delivered alarm');
  clock.now += 7999; run('processCurrentAlarms()');
  assert.equal(run('state.audioDeliverySerial'),1,'Level 2 repeat waits eight seconds');
  clock.now += 1; run('processCurrentAlarms()');
  assert.equal(run('state.audioDeliverySerial'),2,'Continuing level 2 risk repeats after eight seconds');
  video.pause();
  assert.equal(run('state.alarmNodes.size'),0,'Pause stops already scheduled alarm nodes');
  clock.now += 10000; run('processCurrentAlarms({force:true})');
  assert.equal(run('state.audioDeliverySerial'),2,'Paused playback cannot sound even with a forced replay');
  video.paused=false; video.currentTime=5; run('processCurrentAlarms({force:true})');
  assert.equal(run('state.audioDeliverySerial'),2,'A future event without a current matching detection cannot sound');

  activeAlarm();
  audioBehavior.rejectResume=true;
  assert.equal(await run('enableAudio({explicit:true,announceCurrent:true})'),false);
  assert.equal(run('state.notified.size'),0,'A rejected AudioContext resume leaves the active event undelivered');
  assert.ok(element('audio-readiness-text').textContent.includes('chưa cho phát âm'),'Blocked sound exposes an actionable status');
  audioBehavior.rejectResume=false;
  assert.equal(await run('enableAudio({explicit:true,announceCurrent:true})'),true);
  assert.equal(run('state.audioDeliverySerial'),1,'A fresh user gesture retries and delivers the active event once');
  const context=audioContexts.at(-1);
  context.setState('suspended');
  assert.equal(run('state.alarmNodes.size'),0,'Browser suspension stops alarm nodes');
  assert.equal(run('state.audioNeedsReplay'),true);
  await run('enableAudio({explicit:true,announceCurrent:true})');
  assert.equal(run('state.audioDeliverySerial'),2,'AudioContext recovery replays the continuing event once');

  run('muteAudio()');
  assert.equal(storedPreferences.get('aquawatch.audioMuted'),'1');
  assert.equal(run('state.alarmNodes.size'),0,'Mute stops playing nodes immediately');
  assert.equal(run('processCurrentAlarms({force:true})'),false,'Explicit mute suppresses the current event');
  await run('enableAudio({explicit:true,announceCurrent:true})');
  assert.equal(run('state.audioDeliverySerial'),3,'Unmuting announces a still-active event despite its earlier delivery');
  assert.equal(storedPreferences.get('aquawatch.audioMuted'),'0');
  run('muteAudio()');
  await run('armAudioForSelection()');
  run('showVideo({id:"muted-switch",name:"CCTV",url:"/muted.mp4",duration:20});loadAudioPreference()');
  assert.equal(run('state.audioMutedByUser'),true,'Changing clips and reloading settings preserve explicit mute');
  assert.equal(run('audioReady()'),false,'Clip selection never silently unmutes the user');

  activeAlarm();
  audioBehavior.blockedResume=true;
  assert.equal(await run('enableAudio({explicit:true,announceCurrent:true})'),false,'A resolved resume promise is insufficient if the context remains suspended');
  assert.equal(run('state.notified.size'),0);
  audioBehavior.blockedResume=false;
  await run('enableAudio({explicit:true,announceCurrent:true})');
  run('state.volume=0;stopAlarms()');
  assert.equal(run('processCurrentAlarms({force:true})'),false,'Zero app volume cannot mark a new sound as delivered');
  const delivered=run('state.audioDeliverySerial');
  element('volume').value='25'; element('volume').emit('input');
  assert.equal(run('state.audioDeliverySerial'),delivered+1,'Restoring nonzero volume announces the still-active risk');
  run('state.acked.add("danger");stopAlarms()');
  clock.now += 10000; run('processCurrentAlarms({force:true})');
  assert.equal(run('state.audioDeliverySerial'),delivered+1,'Acknowledged events no longer sound');
}
async function autoStartTests() {
  const clips = ['A','B','C','slow'].map((id) => ({id,name:`CCTV ${id}`,url:`/${id}.mp4`,duration:20,width:640,height:360,library:true,camera_mode:'fixed',environment:'pool',above_water:true}));
  const records = new Map();
  const posts = [], cancellations = [], uploads = [];
  let ready = true, pendingPost = null, pendingUpload = null, holdCancel = false, cancellationWait = null;
  let sequence = 0;
  const partial = () => ({partial:true,processed_until:.4,samples:[{time:0,detections:[],motion_known:true},{time:.2,detections:[],motion_known:true},{time:.4,detections:[],motion_known:true}],events:[],duration:20,summary:{}});
  fetchHandler = async (url, options = {}) => {
    if (url === '/api/status') return response({model:{ready,loaded:ready,name:'test',recommended_confidence:.35,device:'test'}});
    if (url === '/api/videos' && options.method === 'POST') {
      uploads.push(options.body);
      const file = options.body.values.get('file');
      const item = {id:`uploaded-${file.name}`,name:file.name,url:'/uploaded.mp4',duration:20,width:640,height:360,camera_mode:'fixed',environment:'pool'};
      if (file.name === 'slow.mp4') return new Promise((resolve) => { pendingUpload = () => resolve(response(item,201)); });
      if (file.name === 'invalid.mp4') return response({detail:'Video cannot be decoded'},422);
      return response(item,201);
    }
    if (url === '/api/videos') return response(clips);
    if (url === '/api/jobs' && options.method === 'POST') {
      const config = JSON.parse(options.body);
      posts.push(config);
      const item = clips.find((clip) => clip.id === config.video_id) || {id:config.video_id,name:config.video_id,url:'/uploaded.mp4',duration:20,width:640,height:360};
      const job = {id:`job-${++sequence}`,status:'running',video:item,config,progress:.02};
      records.set(job.id,job);
      if (config.video_id === 'slow') return new Promise((resolve) => { pendingPost = () => resolve(response({...job},202)); });
      return response({...job},202);
    }
    if (url === '/api/jobs') return response([...records.values()]);
    const cancel = url.match(/^\/api\/jobs\/([^/]+)\/cancel$/);
    if (cancel) {
      cancellations.push(cancel[1]);
      if (holdCancel) cancellationWait = cancel[1];
      else records.get(cancel[1]).status = 'cancelled';
      return response({cancel_requested:true});
    }
    const analysis = url.match(/^\/api\/jobs\/([^/]+)\/analysis$/);
    if (analysis) return response({...partial(),partial:records.get(analysis[1])?.status !== 'completed'});
    const job = url.match(/^\/api\/jobs\/([^/]+)$/);
    if (job) {
      if (cancellationWait === job[1]) { cancellationWait = null; holdCancel = false; return response({...records.get(job[1]),status:'running'}); }
      if (cancellations.includes(job[1])) records.get(job[1]).status = 'cancelled';
      return response({...records.get(job[1])});
    }
    throw new Error(`Unhandled transport ${url}`);
  };
  sandbox.clips = clips;
  element('library-search').value = '';
  run('state.job=null;state.serverJob=null;state.selected=null;state.analysis=null;state.generation=0;state.switching=false;state.uploading=false;state.submitting=false;state.phase="";state.transition=Promise.resolve();state.videos=clips;');
  await run('selectVideo(state.videos[0])'); await flush();
  assert.equal(posts.length,1,'Selection alone starts inference');
  assert.equal(posts[0].mode,'realtime'); assert.equal(posts[0].camera_mode,'fixed'); assert.equal(posts[0].environment,'pool'); assert.equal(posts[0].confidence,.35);
  assert.equal(run('state.selected.id'),'A');
  assert.equal(run('audioReady()'),true,'Selecting a clip arms alarm audio without a second enable button');
  assert.equal(video.muted,true,'Muted source playback does not mute the independent alarm context');
  assert.equal(element('file-input').disabled,false,'Upload remains available during a running session');
  run('renderLibrary()'); assert.ok(!element('library-grid').innerHTML.includes(' disabled'),'Library remains switchable while running');

  holdCancel = true;
  const switching = run('selectVideo(state.videos[1])');
  await until(() => cancellations.length > 0);
  assert.equal(posts.length,1,'New clip cannot submit before cancellation is terminal');
  fireDelay(250);
  await switching; await flush();
  assert.equal(posts.at(-1).video_id,'B');
  assert.equal(records.get('job-1').status,'cancelled');

  const beforeRapid = posts.length;
  run('selectVideo(state.videos[0]);selectVideo(state.videos[2]);');
  await run('state.transition'); await flush();
  assert.equal(posts.length,beforeRapid+1,'Rapid changes submit only the latest waiting clip');
  assert.equal(posts.at(-1).video_id,'C');

  run('selectVideo(state.videos[3])');
  await until(() => pendingPost);
  const staleJob = `job-${sequence}`;
  run('selectVideo(state.videos[0])');
  pendingPost();
  await run('state.transition'); await flush();
  assert.equal(run('state.selected.id'),'A');
  assert.equal(run('state.job.config.video_id'),'A','Late POST result cannot replace the latest source');
  assert.equal(records.get(staleJob).status,'cancelled','Late-created stale job is cancelled before the new submission');

  await run("uploadFile({name:'new.mp4'})"); await flush();
  assert.equal(uploads.at(-1).values.get('above_water'),'true');
  assert.equal(uploads.at(-1).values.get('camera_mode'),'fixed'); assert.equal(uploads.at(-1).values.get('environment'),'pool');
  assert.equal(posts.at(-1).video_id,'uploaded-new.mp4','Upload response starts real-time inference without a second click');

  run("uploadFile({name:'slow.mp4'})"); await until(() => pendingUpload);
  run('selectVideo(state.videos.find((item)=>item.id==="B"))'); pendingUpload();
  await run('state.transition'); await flush();
  assert.equal(run('state.selected.id'),'B');
  assert.ok(!posts.some((config)=>config.video_id==='uploaded-slow.mp4'),'A stale upload response never starts the wrong source');
  assert.ok(run('state.videos.some((item)=>item.id==="uploaded-slow.mp4")'),'Stale successful uploads remain preserved');

  records.set('saved',{id:'saved',status:'completed',video:clips[0],config:{mode:'batch',sample_fps:5}});
  const beforeHistory = posts.length;
  await run("restoreJob('saved')"); await flush();
  assert.equal(posts.length,beforeHistory,'Restoring history never creates another inference job');
  assert.equal(run('state.job.id'),'saved'); assert.equal(run('state.playbackIntent'),false);

  run('state.videos.push({id:"old-smoke",name:"old smoke upload",url:"/old.mp4",library:false});renderLibrary();renderVideoSelect();');
  assert.ok(!element('library-grid').innerHTML.includes('old smoke upload'),'The curated library excludes old smoke uploads');
  assert.ok(!element('video-select').innerHTML.includes('old smoke upload'));

  ready = false;
  const cold = run('selectVideo(state.videos.find((item)=>item.id==="C"))');
  await until(() => run('state.phase').includes('AI đang khởi động') && timers.some((entry)=>entry.milliseconds===500));
  assert.ok(element('stream-label').textContent.includes('AI đang khởi động'),'Cold start is visible and honest');
  ready = true; fireDelay(500); await cold; await flush();
  assert.equal(posts.at(-1).video_id,'C');

  await run("uploadFile({name:'invalid.mp4'})"); await flush();
  assert.equal(run('state.switching'),false);
  assert.ok(element('notice').textContent.includes('Video cannot be decoded'),'Upload errors are shown clearly');
  run('muteAudio()');
  await run('selectVideo(state.videos.find((item)=>item.id==="A"))'); await flush();
  assert.equal(run('state.audioMutedByUser'),true,'The full select-and-autostart flow preserves user mute');
  assert.equal(run('audioReady()'),false);
}

async function main() {
  await new Promise(setImmediate);
  bannerLayoutTest();
  await run('enableAudio({explicit:true})');
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
  assert.ok(!html.includes('id="above-water"'), 'No mandatory camera confirmation checkbox remains');
  assert.ok(html.indexOf('<details class="config-details">') < html.indexOf('id="analyze"'), 'The rerun button belongs to optional advanced controls');
  await audioTests();
  await autoStartTests();
  console.log(`Frontend causal playback checks passed; ${ids.size} HTML element bindings verified.`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
