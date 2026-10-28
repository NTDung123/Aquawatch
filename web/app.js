'use strict';

const $ = (id) => document.getElementById(id);
const LEVELS = ['Chưa thấy dấu hiệu', 'Nghi ngờ', 'Nguy hiểm', 'Khẩn cấp'];
const COLORS = ['#22c6a5', '#f4be45', '#ff6550', '#ff334e'];
const ENVIRONMENTS = { pool: 'Bể bơi', beach: 'Bãi biển', river: 'Sông / hồ', flood: 'Vùng ngập lụt', other: 'Vùng nước khác' };
const SCENARIOS = { normal_swimming: 'Bơi chủ động / nghỉ giữa lượt', negative_background: 'Cảnh nền · không có người', staged_distress: 'Diễn tập dấu hiệu chới với', rescue_assist: 'Tiếp cận / hỗ trợ nổi', staged_passive_float: 'Diễn tập người nổi thụ động', real_rescue: 'Bối cảnh cứu hộ thật' };
const NATURES = { sports_training: 'Tập luyện thể thao', instructional_drill: 'Diễn tập có kiểm soát', ordinary_pool_scene: 'Cảnh bể bơi', real_rescue: 'Cứu hộ thật' };
const REASONS = {
  sustained_drowning: 'Dấu hiệu nguy hiểm kéo dài', drowning_detected: 'Mô hình nhận diện dấu hiệu nghi ngờ',
  model_drowning: 'Mô hình nhận diện dấu hiệu nghi ngờ', temporal_evidence: 'Dấu hiệu tích lũy theo thời gian',
  missing_in_water: 'Mất dấu trong vùng nước đã chọn', missing_after_risk: 'Mất dấu sau dấu hiệu nguy hiểm',
  missing_track: 'Mất dấu đối tượng; cần kiểm tra hình ảnh', camera_motion: 'Góc quan sát đang thay đổi',
  stationary: 'Chuyển động ít; cần kiểm tra', sustained_risk: 'Dấu hiệu nguy hiểm liên tiếp',
  reappeared: 'Đối tượng xuất hiện trở lại', visibility_unknown: 'Không đủ hình ảnh để kết luận'
};
const state = {
  videos: [], selected: null, job: null, analysis: null, jobs: [], polygon: [], drawing: false,
  audio: null, audioEnabled: false, volume: 0.25, notificationEnabled: false,
  notified: new Set(), alarmNodes: new Set(), seeking: false, lastRender: 0, sampleIndex: -1, pollTimer: null,
  modelReady: false, uploading: false, submitting: false, toastTimer: null, eventSignature: '', acked: new Set(),
  realtimeStarting: false, playbackIntent: false, bufferPaused: false, playPending: false, playBlocked: false,
  generation: 0, lastSeekToast: 0
};
const video = $('video');
const canvas = $('overlay');
const ctx = canvas.getContext('2d');

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function timeText(value) {
  const seconds = Math.max(0, Math.floor(Number(value) || 0));
  const h = Math.floor(seconds / 3600);
  return `${h ? `${h}:` : ''}${String(Math.floor(seconds / 60) % 60).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}
function percent(value) { return `${Math.round(Math.min(1, Math.max(0, Number(value) || 0)) * 100)}%`; }
function confidenceText(value) { return value === null || value === undefined ? 'không xác định' : percent(value); }
function reasonsText(reasons) {
  const list = Array.isArray(reasons) ? reasons : reasons ? [reasons] : [];
  return list.map((r) => REASONS[r] || String(r).replaceAll('_', ' ')).join(' · ');
}
function showNotice(message, error = false) {
  $('notice').hidden = !message;
  $('notice').textContent = message || '';
  $('notice').classList.toggle('error', error);
}
function toast(message) {
  clearTimeout(state.toastTimer);
  $('toast').textContent = message;
  $('toast').hidden = false;
  state.toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4500);
}
async function api(path, options = {}) {
  const response = await fetch(path, options);
  let body;
  try { body = await response.json(); } catch (_) { body = null; }
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : `Lỗi máy chủ ${response.status}`);
  }
  return body;
}
function jsonOptions(data) {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) };
}
function activeJob() { return state.job && ['queued', 'running'].includes(state.job.status); }
function isBusy() { return Boolean(activeJob() || state.uploading || state.submitting); }
function isRealtime() { return state.realtimeStarting || state.job?.config?.mode === 'realtime'; }
function hasFrontier() { return isRealtime() && (state.realtimeStarting || state.analysis?.partial !== false || activeJob()); }
function processedUntil() {
  const samples = state.analysis?.samples || [];
  if (!samples.length) return -1;
  return Math.min(Number(state.analysis.processed_until ?? samples[samples.length - 1].time), Number(samples[samples.length - 1].time));
}
function playbackCeiling() {
  return hasFrontier() ? Math.max(0, processedUntil()) : Number(video.duration || state.selected?.duration || 0);
}
function updateControls() {
  const busy = isBusy();
  const unsupportedSource = state.selected?.camera_mode === 'handheld' || state.selected?.above_water === false || state.selected?.view === 'underwater';
  $('analyze').disabled = busy || unsupportedSource || !state.selected || !$('above-water').checked || !state.modelReady || state.drawing;
  $('file-input').disabled = busy;
  $('video-select').disabled = busy;
  $('job-select').disabled = busy;
  $('draw-region').disabled = !state.selected || busy || Boolean(state.analysis);
  $('clear-region').disabled = !state.polygon.length || busy || Boolean(state.analysis);
  $('camera-mode').disabled = Boolean(busy);
  $('environment').disabled = Boolean(busy);
  $('above-water').disabled = Boolean(busy);
  $('sample-fps').disabled = Boolean(busy);
  $('confidence').disabled = Boolean(busy);
  $('analysis-mode').disabled = Boolean(busy);
  const realtime = $('analysis-mode').value === 'realtime';
  $('analysis-hint').textContent = busy ? (isRealtime() ? 'AI phân tích từng phần; video tự chờ khi chưa có kết quả.' : 'Đang phân tích toàn bộ video trên máy…') : unsupportedSource ? 'Nguồn này nằm ngoài phạm vi camera giám sát trên mặt nước; chỉ có thể xem tham khảo.' : !state.selected ? 'Chọn video và xác nhận góc quay để bắt đầu.' : !$('above-water').checked ? 'Cần xác nhận góc quay trên mặt nước.' : !state.modelReady ? 'Model chưa sẵn sàng. Kiểm tra phần cài đặt trên máy chủ.' : realtime ? 'Phát lại video theo thời gian thực. Không kết nối camera vật lý.' : 'Phân tích xong toàn bộ trước khi xem kết quả.';
  $('analyze').innerHTML = realtime ? '<span>▷</span> Bắt đầu giám sát' : state.analysis ? '<span>↻</span> Phân tích lại toàn bộ' : '<span>▷</span> Phân tích toàn bộ';
  $('mode-description').textContent = realtime ? 'Phát lại video có sẵn như một luồng CCTV. AI cập nhật từng phần trong khi video phát.' : 'Xử lý nhanh toàn bộ video rồi phát lại. Có thể xem lại các sự kiện sau khi hoàn tất.';
  document.querySelectorAll('.library-pick').forEach((button) => { button.disabled = Boolean(busy); });
}
async function loadStatus() {
  try {
    const status = await api('/api/status');
    state.modelReady = Boolean(status.model?.ready);
    $('server-dot').style.background = '#13b798';
    $('server-label').textContent = 'Máy chủ đang hoạt động';
    $('metric-model').textContent = status.model?.ready ? (status.model.name || 'Model sẵn sàng') : 'Chưa có model';
    $('metric-model').title = status.model?.name || '';
    $('metric-device').textContent = status.model?.device || 'Xử lý tại máy';
    if (!state.modelReady && status.model?.error) showNotice(`Chưa thể phân tích: ${status.model.error}`, true);
  } catch (_) {
    state.modelReady = false;
    $('server-dot').style.background = '#dc6b6b';
    $('server-label').textContent = 'Mất kết nối máy chủ';
    $('metric-model').textContent = 'Chưa kết nối';
    $('metric-device').textContent = 'Kiểm tra máy chủ local';
  }
  updateControls();
}
async function loadVideos(selectId = null) {
  const response = await api('/api/videos');
  state.videos = Array.isArray(response) ? response : response.videos || [];
  const selectedId = selectId || state.selected?.id || '';
  $('video-select').innerHTML = '<option value="">Chọn video có sẵn</option>' + state.videos.map((item) => `<option value="${escapeHTML(item.id)}">${escapeHTML(item.name)}</option>`).join('');
  $('video-select').value = selectedId;
  renderLibrary();
  if (selectId) selectVideo(state.videos.find((item) => item.id === selectId));
}
function safeLink(value) { try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : ''; } catch (_) { return ''; } }
function searchText(value) { return String(value ?? '').toLowerCase().normalize('NFD').replace(/\p{M}/gu, '').replaceAll('đ', 'd'); }
function cameraLabel(item) {
  if (item.camera_type === 'visually_stable_shore_view_mount_unknown') return 'Góc nhìn ổn định · chưa xác minh vị trí lắp';
  if (item.camera_type?.includes('mount_unknown')) return 'Góc nhìn xoay / zoom · chưa xác minh vị trí lắp';
  return item.camera_mode === 'fixed' ? 'Camera cố định theo khai báo' : item.camera_mode === 'ptz' ? 'Camera PTZ theo khai báo' : item.camera_mode === 'handheld' ? 'Ghi hình cầm tay' : 'Chưa xác minh camera';
}
function benchmarkLabel(item) {
  const role = item.benchmark_role || item.camera_support || '';
  return role.startsWith('primary') ? 'Đoạn góc nhìn ổn định' : role.startsWith('secondary') ? 'Kiểm thử phụ về bối cảnh / chuyển động' : 'Chưa xác định vai trò đánh giá';
}
function videoRole(item) {
  const category = item.category || item.scenario || '';
  if (['normal_swimming', 'negative_background'].includes(category)) return 'negative';
  if (['staged_distress', 'rescue_assist', 'staged_passive_float', 'real_rescue'].includes(category)) return 'positive';
  const value = `${item.benchmark_role || ''} ${category}`.toLowerCase();
  if (/negative|normal|swimming|không sự cố|âm tính/.test(value)) return 'negative';
  if (/positive|rescue|drowning|distress|cứu hộ|nguy cơ/.test(value)) return 'positive';
  return 'unlabeled';
}
function renderLibrary() {
  const query = searchText($('library-search').value.trim());
  const camera = $('library-camera').value;
  const role = $('library-role').value;
  const items = state.videos.filter((item) => (camera === 'all' || item.camera_mode === camera) && (role === 'all' || videoRole(item) === role) && searchText([item.name, item.category, item.scenario, item.source, item.credit, item.license, item.benchmark_role, SCENARIOS[item.category || item.scenario]].join(' ')).includes(query));
  $('library-count').textContent = `${items.length}/${state.videos.length}`;
  if (!items.length) { $('library-grid').innerHTML = '<p class="library-empty">Chưa có video phù hợp. Bạn có thể tải video riêng trong mục Nguồn video.</p>'; return; }
  $('library-grid').innerHTML = items.map((item) => {
    const source = safeLink(item.source_url);
    const itemRole = videoRole(item);
    const roleLabel = SCENARIOS[item.category || item.scenario] || (itemRole === 'negative' ? 'Bơi / cảnh không sự cố' : itemRole === 'positive' ? 'Nguy cơ / cứu hộ' : 'Chưa có nhãn chuẩn');
    const thumb = item.thumbnail_url || item.poster_url;
    return `<article class="library-card${state.selected?.id === item.id ? ' selected' : ''}"><button class="library-pick" data-video-id="${escapeHTML(item.id)}"${isBusy() ? ' disabled' : ''} aria-label="Chọn ${escapeHTML(item.name)}"><div class="library-preview">${thumb ? `<img src="${escapeHTML(thumb)}" alt="Khung hình video ${escapeHTML(item.name)}" loading="lazy">` : `<video src="${escapeHTML(item.url)}" muted playsinline preload="metadata" tabindex="-1" aria-hidden="true"></video>`}<span class="library-play">▷</span><time>${timeText(item.duration)}</time></div><div class="library-card-copy"><span class="library-camera">${escapeHTML(cameraLabel(item))}</span><h3>${escapeHTML(item.name)}</h3><p class="library-role ${itemRole}">${escapeHTML(roleLabel)}</p><small class="library-nature">${escapeHTML(NATURES[item.nature] || (item.library ? 'Video nguồn công khai đã sàng lọc' : 'Video người dùng'))}${Number(item.scene_cuts) > 0 ? ` · ${Number(item.scene_cuts)} lần cắt cảnh` : ''}</small></div></button><div class="library-rights"><span title="${escapeHTML(item.credit || item.source || '')}">${escapeHTML(item.license || 'Quyền sử dụng do người tải chịu trách nhiệm')}</span>${source ? `<a href="${escapeHTML(source)}" target="_blank" rel="noopener">Nguồn ↗</a>` : ''}</div></article>`;
  }).join('');
}
async function loadJobs() {
  const response = await api('/api/jobs');
  state.jobs = (Array.isArray(response) ? response : response.jobs || []).sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  const selectedId = state.job?.id || '';
  const statuses = { completed: 'Đã hoàn tất', running: 'Đang xử lý', queued: 'Đang chờ', failed: 'Thất bại', cancelled: 'Đã hủy' };
  $('job-select').innerHTML = '<option value="">Chọn kết quả trước đây</option>' + state.jobs.map((item) => `<option value="${escapeHTML(item.id)}">${escapeHTML(item.video?.name || item.id.slice(0, 8))} · ${statuses[item.status] || item.status}</option>`).join('');
  $('job-select').value = selectedId;
}
async function loadAnalysis(job, reset = false) {
  const generation = state.generation;
  const result = await api(`/api/jobs/${encodeURIComponent(job.id)}/analysis`);
  if (generation !== state.generation || state.job?.id !== job.id) return;
  state.analysis = result;
  state.analysis.partial = job.status !== 'completed';
  state.analysis.samples = (state.analysis.samples || []).slice().sort((a, b) => Number(a.time) - Number(b.time));
  state.polygon = job.config?.water_polygon || [];
  $('analysis-progress').hidden = !activeJob();
  $('export-controls').hidden = state.analysis.partial;
  $('export-json').href = `/api/jobs/${encodeURIComponent(job.id)}/export?format=json`;
  $('export-csv').href = `/api/jobs/${encodeURIComponent(job.id)}/export?format=csv`;
  if (reset) video.currentTime = 0;
  if (!isRealtime()) $('playback-state').textContent = state.analysis.partial ? 'Kết quả một phần · phiên chưa hoàn tất' : 'Kết quả sẵn sàng · nhấn phát để giám sát';
  $('review-mode').disabled = Boolean(activeJob());
  if (activeJob()) $('review-mode').checked = false;
  state.eventSignature = '';
  updatePerformance();
  renderFrame(true);
  enforceBuffer();
  updateStreamStatus();
}
async function restoreJob(id) {
  if (!id || isBusy()) return;
  try {
    const job = await api(`/api/jobs/${encodeURIComponent(id)}`);
    const source = state.videos.find((item) => item.id === job.video?.id) || job.video;
    if (!source?.url) throw new Error('Không tìm thấy video gốc của phiên phân tích.');
    selectVideo(source);
    state.job = job;
    $('job-select').value = id;
    $('camera-mode').value = job.config?.camera_mode || source.camera_mode || 'fixed';
    $('analysis-mode').value = job.config?.mode || 'batch';
    $('sample-fps').value = String(job.config?.sample_fps || 5);
    $('confidence').value = String(job.config?.confidence || .4);
    $('confidence-value').textContent = Number($('confidence').value).toFixed(2);
    updateMode();
    if (job.status === 'completed') await loadAnalysis(job, true);
    else if (['running', 'queued'].includes(job.status)) { $('analysis-progress').hidden = false; await pollJob(); }
    else { try { await loadAnalysis(job, true); } catch (_) { /* A failed early job may have no snapshot. */ } showNotice(job.error || `Phiên này ${job.status === 'cancelled' ? 'đã được hủy' : 'chưa hoàn tất'}. Chỉ xem được phần đã phân tích.`, job.status === 'failed'); }
    updateControls();
  } catch (error) { showNotice(`Không mở được kết quả đã lưu: ${error.message}`, true); }
}
function updatePerformance() {
  const summary = state.analysis?.summary;
  $('performance-summary').hidden = !summary || !$('review-mode').checked;
  if (!summary) return;
  const milliseconds = summary.mean_inference_ms === null || summary.mean_inference_ms === undefined ? '—' : `${Number(summary.mean_inference_ms).toFixed(1)} ms`;
  $('performance-summary').textContent = `Đo hiệu năng thực tế: ${summary.processing_seconds ?? '—'} giây xử lý · ${summary.samples ?? state.analysis.samples.length} mẫu · ${milliseconds}/mẫu · ${summary.sample_throughput_fps ?? '—'} mẫu/giây. Chưa có chỉ số độ chính xác độc lập.`;
}
async function attemptPlay(userGesture = false) {
  if (state.playPending || (state.playBlocked && !userGesture)) return;
  state.playBlocked = false;
  state.playPending = true;
  try {
    await video.play();
  } catch (error) {
    if (error.name !== 'AbortError') {
      state.playBlocked = true;
      if (error.name === 'NotAllowedError') toast('Trình duyệt yêu cầu thao tác phát. Nhấn “Phát giám sát” khi có bộ đệm.');
      else showNotice('Không thể phát video. Kiểm tra codec hoặc thử MP4 H.264; có thể nhấn phát lại sau khi nguồn tải xong.', true);
    }
  } finally { state.playPending = false; updateStreamStatus(); }
}
function enforceBuffer() {
  if (!isRealtime()) return;
  const watermark = processedUntil();
  const ceiling = playbackCeiling();
  const bounded = hasFrontier();
  if (bounded && video.currentTime > ceiling + .01) {
    video.currentTime = ceiling;
  }
  const available = watermark - (video.currentTime || 0);
  if (bounded && (watermark < 0 || available <= .06)) {
    state.bufferPaused = true;
    if (!video.paused) video.pause();
    if (!activeJob() && !state.realtimeStarting) state.playbackIntent = false;
  } else if (state.bufferPaused && state.playbackIntent && !state.playBlocked && (available >= .8 || !bounded || (!activeJob() && available > .15))) {
    state.bufferPaused = false;
    attemptPlay();
  }
  updateStreamStatus();
}
function updateStreamStatus() {
  $('stream-status').hidden = !isRealtime();
  if (!isRealtime()) return;
  const watermark = processedUntil();
  const available = Math.max(0, watermark - (video.currentTime || 0));
  const elapsed = Number(state.analysis?.source_elapsed_seconds ?? state.job?.source_elapsed_seconds) || 0;
  const lag = watermark >= 0 ? Math.max(0, elapsed - watermark) : 0;
  const stopped = !activeJob() && !state.realtimeStarting && state.analysis?.partial;
  $('stream-label').textContent = state.playBlocked ? 'Cần nhấn phát trên thiết bị' : stopped && available < .1 ? 'Đã hết phần kết quả được lưu' : state.bufferPaused ? 'Đang chờ kết quả AI' : !state.playbackIntent && video.paused ? 'Đã tạm dừng giám sát' : 'CCTV phát lại · đang giám sát';
  $('stream-detail').textContent = watermark < 0 ? 'Đang khởi tạo model và chờ mẫu đầu tiên. Không kết nối camera vật lý.' : `AI đến ${timeText(watermark)} · bộ đệm ${available.toFixed(1)}s · trễ xử lý ${lag.toFixed(1)}s · ${state.analysis?.samples?.length || 0} mẫu`;
  $('stream-indicator').className = `buffer-dot${state.bufferPaused || state.playBlocked ? ' waiting' : ''}`;
  $('stream-play').textContent = state.playBlocked ? 'Nhấn để phát' : state.playbackIntent ? 'Tạm dừng phát' : 'Phát giám sát';
  $('playback-state').textContent = state.bufferPaused ? 'Chờ AI · video không vượt phần đã phân tích' : video.paused ? 'Đã tạm dừng · kết quả tiếp tục được lưu' : 'Đang phát lại CCTV theo thời gian video';
}
function selectVideo(item) {
  if (isBusy()) return;
  video.pause();
  state.generation += 1;
  clearTimeout(state.pollTimer);
  state.selected = item || null;
  state.job = null;
  state.analysis = null;
  state.polygon = [];
  state.notified.clear();
  state.acked.clear();
  state.eventSignature = '';
  state.sampleIndex = -1;
  state.realtimeStarting = false;
  state.playbackIntent = false;
  state.bufferPaused = false;
  state.playBlocked = false;
  stopDrawing();
  $('review-mode').checked = false;
  $('export-controls').hidden = true;
  $('performance-summary').hidden = true;
  $('job-select').value = '';
  $('analysis-progress').hidden = true;
  $('stream-status').hidden = true;
  $('review-mode').disabled = false;
  $('alert-banner').hidden = true;
  $('empty-video').hidden = Boolean(item);
  $('video-wrap').hidden = !item;
  $('source-info').hidden = !item;
  $('above-water').checked = false;
  if (item) {
    $('video-select').value = item.id;
    video.src = item.url;
    video.load();
    $('video-name').textContent = item.name;
    $('metric-source').textContent = item.name.replace(/\.[^.]+$/, '');
    $('metric-source').title = item.name;
    $('metric-source-detail').textContent = `${item.width || '—'} × ${item.height || '—'} · ${timeText(item.duration)}`;
    const sourceLink = safeLink(item.source_url);
    const licenseLink = safeLink(item.license_url);
    $('source-info').innerHTML = `<strong>${item.width || '—'} × ${item.height || '—'} · ${timeText(item.duration)}${item.fps ? ` · ${Number(item.fps).toFixed(1)} FPS` : ''}</strong><span>${escapeHTML(SCENARIOS[item.category || item.scenario] || 'Chưa có nhãn tình huống chuẩn')}${NATURES[item.nature] ? ` · ${escapeHTML(NATURES[item.nature])}` : ''}</span><span>${escapeHTML(cameraLabel(item))}</span>${item.library ? `<span>${escapeHTML(benchmarkLabel(item))}. ${item.split === 'video_library_holdout_do_not_train' ? 'Không dùng trong huấn luyện cục bộ; chưa xác minh trùng dữ liệu pretrained.' : ''}</span>` : ''}${item.credit || item.source ? `<span class="source-credit">${escapeHTML(item.credit || item.source)}</span>` : ''}<div class="source-links">${sourceLink ? `<a href="${escapeHTML(sourceLink)}" target="_blank" rel="noopener">Nguồn gốc ↗</a>` : ''}${licenseLink ? `<a href="${escapeHTML(licenseLink)}" target="_blank" rel="noopener">Giấy phép ↗</a>` : ''}</div>`;
    $('camera-mode').value = ['fixed', 'ptz'].includes(item.camera_mode) ? item.camera_mode : 'fixed';
    $('environment').value = item.environment || 'pool';
    $('playback-state').textContent = 'Nguồn sẵn sàng · chưa phân tích';
  } else {
    video.removeAttribute('src');
    video.load();
    $('metric-source').textContent = 'Chưa chọn';
    $('metric-source-detail').textContent = 'Video giám sát trên mặt nước';
    $('playback-state').textContent = 'Chờ nguồn video';
  }
  $('region-hint').textContent = 'Đánh dấu vùng nước để hỗ trợ giả thuyết mất dấu. Không vẽ nếu chưa biết rõ khu vực.';
  updateMode();
  renderFrame(true);
  updateControls();
  renderLibrary();
  showNotice('');
}
async function uploadFile(file) {
  if (!file || isBusy()) return;
  if (!$('above-water').checked) {
    showNotice('Trước khi tải lên, hãy xác nhận video được ghi bằng camera ở phía trên mặt nước.');
    $('above-water').focus();
    $('file-input').value = '';
    return;
  }
  state.uploading = true;
  updateControls();
  $('analysis-hint').textContent = `Đang tải ${file.name}…`;
  const form = new FormData();
  form.append('file', file);
  form.append('above_water', 'true');
  form.append('camera_mode', $('camera-mode').value);
  form.append('environment', $('environment').value);
  try {
    const item = await api('/api/videos', { method: 'POST', body: form });
    state.uploading = false;
    await loadVideos(item.id);
    $('above-water').checked = true;
    updateControls();
    toast('Đã tải video. Bạn có thể vẽ vùng nước và bắt đầu phân tích.');
  } catch (error) { showNotice(`Tải video thất bại: ${error.message}`, true); }
  finally { state.uploading = false; $('file-input').value = ''; updateControls(); }
}
function updateMode() {
  const ptz = $('camera-mode').value === 'ptz';
  $('video-mode-label').textContent = ptz ? 'Camera PTZ' : 'Camera cố định';
}
function stopDrawing() {
  state.drawing = false;
  $('video-stage').classList.remove('drawing');
  $('draw-region').textContent = '⌖ Vẽ vùng nước';
}
function contentRect() {
  const w = video.clientWidth || canvas.clientWidth;
  const h = video.clientHeight || canvas.clientHeight;
  const ratio = video.videoWidth && video.videoHeight ? video.videoWidth / video.videoHeight : w / h;
  let width = w, height = w / ratio;
  if (height > h) { height = h; width = h * ratio; }
  return { x: (w - width) / 2, y: (h - height) / 2, width, height };
}
function resizeCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const width = video.clientWidth || 640;
  const height = video.clientHeight || 360;
  if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
  }
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}
function sampleAt(time) {
  const samples = state.analysis?.samples || [];
  let low = 0, high = samples.length - 1, found = -1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (Number(samples[mid].time) <= time + 0.001) { found = mid; low = mid + 1; }
    else high = mid - 1;
  }
  if (found < 0) return null;
  const sample = samples[found];
  const gap = Math.max(0.7, 2 / (Number(state.job?.config?.sample_fps) || Number($('sample-fps').value) || 5));
  if (time - Number(sample.time) > gap) return null;
  return { sample, index: found };
}
function drawPolygon(rect) {
  if (!state.polygon.length) return;
  ctx.beginPath();
  state.polygon.forEach(([x, y], index) => {
    if (index === 0) ctx.moveTo(rect.x + x * rect.width, rect.y + y * rect.height);
    else ctx.lineTo(rect.x + x * rect.width, rect.y + y * rect.height);
  });
  if (state.polygon.length >= 3) ctx.closePath();
  ctx.fillStyle = '#15c4be15';
  ctx.strokeStyle = '#48ddd0';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([5, 4]);
  if (state.polygon.length >= 3) ctx.fill();
  ctx.stroke();
  ctx.setLineDash([]);
  if (state.drawing) state.polygon.forEach(([x, y]) => { ctx.beginPath(); ctx.arc(rect.x + x * rect.width, rect.y + y * rect.height, 3, 0, 2 * Math.PI); ctx.fillStyle = '#6ff3df'; ctx.fill(); });
}
function drawDetection(detection, rect) {
  const box = detection.box || detection.bbox;
  if (!Array.isArray(box) || box.length < 4) return;
  const level = Math.max(0, Math.min(3, Number(detection.level) || 0));
  const [x1, y1, x2, y2] = box.map(Number);
  if (![x1, y1, x2, y2].every(Number.isFinite)) return;
  const x = rect.x + Math.max(0, x1) * rect.width;
  const y = rect.y + Math.max(0, y1) * rect.height;
  const w = Math.min(1, x2) * rect.width + rect.x - x;
  const h = Math.min(1, y2) * rect.height + rect.y - y;
  if (w <= 0 || h <= 0) return;
  ctx.strokeStyle = COLORS[level];
  ctx.lineWidth = level >= 2 ? 3 : 1.7;
  if (detection.inferred) ctx.setLineDash([7, 5]);
  ctx.strokeRect(x, y, w, h);
  ctx.setLineDash([]);
  const label = detection.inferred || detection.label === 'missing' ? 'Vị trí cuối · mất dấu chưa xác nhận' : detection.label === 'swimming' ? 'Bơi / người trong nước' : detection.label === 'drowning' ? 'Dấu hiệu nghi ngờ' : (detection.label || 'Đối tượng');
  const text = `#${detection.track_id ?? '?'} ${label}${detection.inferred ? '' : ` · ${confidenceText(detection.confidence)}`} · ${LEVELS[level]}`;
  const fontSize = Math.max(9, Math.min(12, rect.width / 55));
  ctx.font = `600 ${fontSize}px "Segoe UI", sans-serif`;
  const tw = Math.min(ctx.measureText(text).width + 12, rect.width);
  const labelX = Math.max(rect.x, Math.min(x, rect.x + rect.width - tw));
  const labelY = Math.max(rect.y + 1, y - fontSize - 9);
  ctx.fillStyle = COLORS[level];
  ctx.fillRect(labelX, labelY, tw, fontSize + 7);
  ctx.fillStyle = '#06191d';
  ctx.fillText(text, labelX + 5, labelY + fontSize + 1, tw - 10);
}
function currentEvents(time) {
  return (state.analysis?.events || []).filter((event) => Number(event.start) <= time + 0.001 && (event.end === null || event.end === undefined || time <= Number(event.end) + 0.35));
}
function renderFrame(force = false) {
  resizeCanvas();
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const rect = contentRect();
  drawPolygon(rect);
  const time = video.currentTime || 0;
  const result = sampleAt(time);
  const sample = result?.sample;
  const detections = sample?.detections || [];
  detections.forEach((d) => drawDetection(d, rect));
  $('video-time').textContent = `${timeText(time)} / ${timeText(video.duration || state.selected?.duration)}`;
  if (!force && result?.index === state.sampleIndex) return;
  state.sampleIndex = result?.index ?? -1;
  $('metric-objects').textContent = state.analysis ? String(detections.filter((d) => !d.inferred).length) : '—';
  let level = Math.max(0, Math.min(3, Number(sample?.level) || 0));
  const events = currentEvents(time);
  const riskEvents = events.filter((e) => Number(e.level) > 0);
  if (!sample && !riskEvents.length) level = 0;
  const observationLimited = !sample || !detections.some((d) => !d.inferred) || sample.camera_moving || !sample.motion_known;
  $('metric-level').textContent = state.analysis ? (observationLimited ? 'Không đủ quan sát' : LEVELS[level]) : 'Chưa phân tích';
  $('metric-level').className = level >= 2 ? 'danger' : level === 1 || (state.analysis && observationLimited) ? 'suspicious' : '';
  $('metric-level-detail').textContent = state.analysis && observationLimited ? (sample?.camera_moving ? 'Góc nhìn thay đổi · chưa thể kết luận an toàn' : 'Thiếu hình ảnh/mốc nền · chưa thể kết luận an toàn') : state.analysis ? `Tại thời điểm ${timeText(time)} · không xác nhận an toàn` : 'Đánh giá theo diễn biến video';
  if (state.analysis && state.polygon.length >= 3) {
    $('region-hint').textContent = !sample?.missing_inference_enabled ? 'Giả thuyết mất dấu đang tắt: góc nhìn thay đổi hoặc thiếu mốc nền. Cần phân tích lại và vẽ vùng phù hợp.' : 'Giả thuyết mất dấu đang bật trong vùng đã chọn. Mất dấu không xác nhận đã chìm hoặc đã an toàn.';
  }
  const actualRiskEvents = sample ? riskEvents.filter((event) => detections.some((d) => d.track_id === event.track_id && Number(d.level) === Number(event.level))) : [];
  const best = actualRiskEvents.sort((a, b) => Number(b.level) - Number(a.level))[0];
  const bannerLevel = sample ? level : 0;
  $('alert-banner').hidden = bannerLevel < 1 || !state.analysis;
  if (bannerLevel >= 1) {
    $('alert-banner').className = `alert-banner level${bannerLevel}`;
    $('alert-title').textContent = `${LEVELS[bannerLevel]}${best ? ` · Đối tượng #${best.track_id}` : ''}`;
    $('alert-description').textContent = sample?.camera_moving ? 'Camera đang thay đổi góc nhìn. Kiểm tra hình ảnh trước khi suy luận mất dấu.' : reasonsText(best?.reasons || detections.filter((d) => Number(d.level) > 0).flatMap((d) => d.reasons || [])) || 'Kiểm tra trực tiếp đối tượng và khu vực được đánh dấu.';
  }
  renderEvents();
  if (!video.paused && !state.seeking) actualRiskEvents.forEach(notifyEvent);
}
function renderEvents() {
  const all = state.analysis?.events || [];
  const review = $('review-mode').checked && !activeJob() && !state.realtimeStarting;
  const events = all.filter((event) => review || Number(event.start) <= (video.currentTime || 0) + 0.001);
  const signature = `${state.job?.id}:${review}:${events.map((e) => `${e.id}:${e.acknowledged || state.acked.has(e.id)}`).join(',')}`;
  if (signature === state.eventSignature) { renderTimeline(events, review); return; }
  state.eventSignature = signature;
  $('events-count').textContent = String(events.length);
  $('event-help').textContent = review ? 'Chế độ xem lại: hiển thị toàn bộ sự kiện đã phân tích. Chọn một sự kiện để tua tới bằng chứng.' : 'Chế độ giám sát: chỉ hiển thị sự kiện đã xuất hiện đến thời điểm video đang xem.';
  $('timeline').innerHTML = '';
  if (!events.length) {
    $('event-list').innerHTML = `<div class="empty-events"><span>◷</span><strong>${state.analysis ? 'Chưa có sự kiện ở thời điểm đang xem' : 'Chưa có sự kiện để hiển thị'}</strong><p>${state.analysis ? 'Tiếp tục phát video hoặc bật chế độ xem lại toàn bộ.' : 'Lịch sử và ảnh bằng chứng sẽ được lưu sau khi phân tích.'}</p></div>`;
    return;
  }
  $('event-list').innerHTML = events.slice().reverse().map((event) => {
    const level = Math.max(0, Math.min(3, Number(event.level) || 0));
    const ack = event.acknowledged || state.acked.has(event.id);
    return `<article class="event-row"><time class="event-time">${timeText(event.start)}</time><span class="event-indicator" style="background:${COLORS[level]}"></span><div class="event-detail"><button class="event-seek" data-seek="${Number(event.start)}"><strong>${escapeHTML(LEVELS[level])} · Đối tượng #${escapeHTML(event.track_id ?? '?')}</strong></button><p>${escapeHTML(reasonsText(event.reasons) || 'Kiểm tra dấu hiệu tại khung hình được đánh dấu.')}</p><div class="event-actions"><span class="muted">Tin cậy ${confidenceText(event.confidence)}</span><button class="text-button" data-seek="${Number(event.start)}">Xem tại ${timeText(event.start)}</button>${ack ? '<span class="event-badge">Đã xác nhận</span>' : `<button class="text-button" data-ack="${escapeHTML(event.id)}">Xác nhận đã xem</button>`}</div></div>${event.evidence_url ? `<a href="${escapeHTML(event.evidence_url)}" target="_blank" rel="noopener" aria-label="Mở ảnh bằng chứng"><img class="evidence-image" loading="lazy" src="${escapeHTML(event.evidence_url)}" alt="Bằng chứng tại ${timeText(event.start)}"></a>` : ''}</article>`;
  }).join('');
  renderTimeline(events, review);
}
function renderTimeline(events, review) {
  $('timeline').innerHTML = '';
  const duration = state.analysis?.duration || state.selected?.duration || video.duration || 1;
  events.forEach((event) => {
    const marker = document.createElement('button');
    const start = Math.max(0, Math.min(100, Number(event.start) / duration * 100));
    const end = Math.min(duration, Number(event.end ?? event.start), review ? duration : (video.currentTime || 0));
    marker.style.left = `${start}%`;
    marker.style.width = `${Math.min(100 - start, Math.max(.6, (end - Number(event.start)) / duration * 100))}%`;
    marker.style.background = COLORS[Math.min(3, Number(event.level) || 0)];
    marker.title = `${LEVELS[event.level] || 'Sự kiện'} · ${timeText(event.start)}`;
    marker.setAttribute('aria-label', marker.title);
    marker.addEventListener('click', () => seekVideo(Number(event.start)));
    $('timeline').appendChild(marker);
  });
}
function seekVideo(time) {
  state.playbackIntent = false;
  state.bufferPaused = false;
  video.pause();
  const target = Math.max(0, Math.min(time, playbackCeiling() || 0));
  state.seeking = Math.abs((video.currentTime || 0) - target) > .001;
  video.currentTime = target;
  renderFrame(true);
}
async function startAnalysis() {
  if (!state.selected || !$('above-water').checked || isBusy()) return;
  state.submitting = true;
  video.pause();
  state.generation += 1;
  const generation = state.generation;
  const mode = $('analysis-mode').value;
  state.job = null;
  state.realtimeStarting = mode === 'realtime';
  state.playbackIntent = mode === 'realtime';
  state.bufferPaused = mode === 'realtime';
  state.playBlocked = false;
  video.currentTime = 0;
  video.playbackRate = 1;
  updateControls();
  stopDrawing();
  showNotice('');
  state.analysis = null;
  state.eventSignature = '';
  state.sampleIndex = -1;
  state.notified.clear();
  state.acked.clear();
  $('export-controls').hidden = true;
  $('performance-summary').hidden = true;
  $('analysis-progress').hidden = false;
  $('progress-percent').textContent = '0%';
  $('progress-bar').value = 0;
  $('review-mode').checked = false;
  $('review-mode').disabled = true;
  $('progress-help').textContent = mode === 'realtime' ? 'Video có sẵn được đọc tuần tự theo thời gian. AI cập nhật từng phần; video tự chờ khi chưa đủ kết quả. Không kết nối camera vật lý.' : 'Phân tích trước toàn bộ video. Cảnh báo khi phát lại chỉ dùng dữ liệu tại thời điểm đang xem.';
  if (mode === 'realtime') attemptPlay(true);
  updateStreamStatus();
  try {
    const job = await api('/api/jobs', jsonOptions({ video_id: state.selected.id, mode, camera_mode: $('camera-mode').value, environment: $('environment').value, above_water: true, water_polygon: state.polygon.length >= 3 ? state.polygon : [], sample_fps: Number($('sample-fps').value), confidence: Number($('confidence').value) }));
    if (generation !== state.generation) return;
    state.job = job;
    state.realtimeStarting = false;
    state.submitting = false;
    updateControls();
    renderFrame(true);
    await pollJob();
  } catch (error) {
    state.realtimeStarting = false;
    state.playbackIntent = false;
    state.submitting = false;
    video.pause();
    $('analysis-progress').hidden = true;
    showNotice(`Không thể bắt đầu phân tích: ${error.message}`, true);
    updateControls();
  }
}
async function pollJob() {
  clearTimeout(state.pollTimer);
  if (!state.job) return;
  const id = state.job.id;
  try {
    const job = await api(`/api/jobs/${encodeURIComponent(id)}`);
    if (state.job?.id !== id) return;
    state.job = job;
    const progress = Number(job.progress) || 0;
    const p = Math.min(100, Math.max(0, progress <= 1 ? progress * 100 : progress));
    $('progress-percent').textContent = `${Math.round(p)}%`;
    $('progress-bar').value = p;
    $('progress-label').textContent = job.status === 'queued' ? 'Đang chờ bộ phân tích…' : isRealtime() ? 'Đang giám sát tuần tự theo thời gian video…' : 'Đang phân tích toàn bộ video…';
    if (!isRealtime()) $('playback-state').textContent = 'Đang phân tích trước video';
    if (job.status === 'completed') {
      await loadAnalysis(job, !isRealtime());
      await loadJobs();
      $('analysis-progress').hidden = true;
      toast(isRealtime() ? 'Đã phân tích hết nguồn video. Có thể xem lại toàn bộ sự kiện.' : 'Đã phân tích xong. Nhấn phát video để xem kết quả theo thời gian.');
      updateControls();
      return;
    }
    if (['failed', 'cancelled'].includes(job.status)) {
      try { await loadAnalysis(job); } catch (_) { /* An early failure can precede the first snapshot. */ }
      $('analysis-progress').hidden = true;
      showNotice(job.status === 'cancelled' ? 'Đã dừng phân tích. Chỉ phần đã xử lý được lưu; đây không phải kết quả hoàn tất toàn bộ video.' : `Phân tích thất bại: ${job.error || 'Kiểm tra nhật ký máy chủ.'}. Có thể xem lại phần đã lưu.`, job.status === 'failed');
      $('playback-state').textContent = job.status === 'cancelled' ? 'Đã hủy phân tích' : 'Phân tích thất bại';
      updateControls();
      return;
    }
    if (isRealtime()) {
      try { await loadAnalysis(job); } catch (error) { if (!error.message.includes('Chưa có kết quả')) throw error; }
      enforceBuffer();
    }
    updateControls();
    state.pollTimer = setTimeout(pollJob, 1000);
  } catch (error) {
    showNotice(`Chưa lấy được tiến độ: ${error.message}. Hệ thống sẽ thử lại.`, true);
    state.pollTimer = setTimeout(pollJob, 3000);
  }
}
async function enableAudio() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) { toast('Trình duyệt này không hỗ trợ Web Audio.'); return false; }
  try {
    if (!state.audio) state.audio = new AudioContextClass();
    await state.audio.resume();
    state.audioEnabled = state.audio.state === 'running';
    updateAudioUI();
    return state.audioEnabled;
  } catch (_) { toast('Không thể kích hoạt âm thanh. Kiểm tra quyền của trình duyệt.'); return false; }
}
function updateAudioUI() {
  $('enable-audio').textContent = state.audioEnabled ? 'Tắt' : 'Bật';
  $('audio-state').textContent = state.audioEnabled ? `Đã bật · âm lượng ${Math.round(state.volume * 100)}%` : 'Âm thanh đang tắt';
  $('banner-mute').title = state.audioEnabled ? 'Tắt âm cảnh báo' : 'Âm cảnh báo đang tắt';
}
function playAlarm(level = 2) {
  if (!state.audioEnabled || !state.audio || state.audio.state !== 'running' || !state.volume) return;
  const now = state.audio.currentTime;
  const count = level === 3 ? 4 : level === 2 ? 3 : 2;
  for (let i = 0; i < count; i++) {
    const start = now + i * .32;
    const oscillator = state.audio.createOscillator();
    const gain = state.audio.createGain();
    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(level >= 2 ? 730 : 520, start);
    oscillator.frequency.linearRampToValueAtTime(level === 3 ? 1100 : level === 2 ? 930 : 620, start + .18);
    gain.gain.setValueAtTime(0, start);
    gain.gain.linearRampToValueAtTime(state.volume * .35, start + .025);
    gain.gain.exponentialRampToValueAtTime(.001, start + .24);
    oscillator.connect(gain);
    gain.connect(state.audio.destination);
    const nodes = { oscillator, gain };
    state.alarmNodes.add(nodes);
    oscillator.start(start);
    oscillator.stop(start + .26);
    oscillator.onended = () => { state.alarmNodes.delete(nodes); oscillator.disconnect(); gain.disconnect(); };
  }
}
function stopAlarms() {
  for (const { oscillator, gain } of state.alarmNodes) {
    gain.gain.cancelScheduledValues(0);
    gain.gain.setValueAtTime(0, state.audio.currentTime);
    try { oscillator.stop(); } catch (_) { /* Already-ended oscillators need no action. */ }
  }
  state.alarmNodes.clear();
}
function notifyEvent(event) {
  const key = `${state.job?.id}:${event.id}:${event.level}`;
  if (state.notified.has(key) || event.acknowledged || state.acked.has(event.id)) return;
  state.notified.add(key);
  playAlarm(Number(event.level) || 1);
  if ($('enable-vibration').checked && typeof navigator.vibrate === 'function') navigator.vibrate(Number(event.level) >= 2 ? [160, 90, 160] : [100]);
  if (state.notificationEnabled && window.Notification?.permission === 'granted') {
    try { new Notification(`AquaWatch · ${LEVELS[event.level] || 'Cảnh báo'}`, { body: `Đối tượng #${event.track_id} · ${timeText(event.start)}. Kiểm tra video trực tiếp.`, tag: key, silent: true }); } catch (_) { /* Notification constructors may be unavailable on mobile. */ }
  }
}
function capabilityUI() {
  const notificationSupported = 'Notification' in window && window.isSecureContext;
  $('enable-notifications').disabled = !notificationSupported;
  $('notification-state').textContent = !('Notification' in window) ? 'Trình duyệt không hỗ trợ' : !window.isSecureContext ? 'Cần HTTPS hoặc localhost' : Notification.permission === 'denied' ? 'Quyền đã bị từ chối' : 'Chưa bật trên thiết bị này';
  $('enable-vibration').disabled = typeof navigator.vibrate !== 'function';
  const vibration = typeof navigator.vibrate === 'function' ? 'Có API rung; thiết bị có thể không phản hồi.' : 'Thiết bị này không có API rung.';
  $('capability-note').textContent = `Âm thanh cần thao tác bật và phụ thuộc âm lượng hệ thống. ${vibration} Thông báo cần quyền và ngữ cảnh bảo mật; không bảo đảm hoạt động khi đóng trang.`;
}

$('video-select').addEventListener('change', (event) => selectVideo(state.videos.find((item) => item.id === event.target.value)));
$('job-select').addEventListener('change', (event) => restoreJob(event.target.value));
$('analysis-mode').addEventListener('change', updateControls);
['library-search', 'library-camera', 'library-role'].forEach((id) => $(id).addEventListener(id === 'library-search' ? 'input' : 'change', renderLibrary));
$('refresh-library').addEventListener('click', () => loadVideos().then(() => toast('Đã làm mới thư viện.')).catch((error) => showNotice(error.message, true)));
$('library-grid').addEventListener('click', (event) => { const button = event.target.closest('[data-video-id]'); if (!button || button.disabled) return; selectVideo(state.videos.find((item) => item.id === button.dataset.videoId)); $('monitor').scrollIntoView({ behavior: 'smooth', block: 'start' }); });
$('stream-play').addEventListener('click', () => {
  if (state.playbackIntent && !state.playBlocked) { state.playbackIntent = false; state.bufferPaused = false; video.pause(); }
  else { state.playbackIntent = true; state.playBlocked = false; state.bufferPaused = false; attemptPlay(true); enforceBuffer(); }
  updateStreamStatus();
});
$('empty-upload').addEventListener('click', () => { $('source-panel').scrollIntoView({ behavior: 'smooth', block: 'center' }); if ($('above-water').checked) $('file-input').click(); else { showNotice('Hãy xác nhận góc quay trên mặt nước trong mục Nguồn video, sau đó chọn tệp.'); $('above-water').focus(); } });
$('file-input').addEventListener('change', (event) => uploadFile(event.target.files[0]));
const uploadZone = document.querySelector('.upload-zone');
uploadZone.tabIndex = 0;
uploadZone.setAttribute('role', 'button');
uploadZone.setAttribute('aria-label', 'Chọn video để tải lên');
uploadZone.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); if (!$('file-input').disabled) $('file-input').click(); } });
['dragenter', 'dragover'].forEach((name) => uploadZone.addEventListener(name, (event) => { event.preventDefault(); uploadZone.classList.add('dragging'); }));
['dragleave', 'drop'].forEach((name) => uploadZone.addEventListener(name, (event) => { event.preventDefault(); uploadZone.classList.remove('dragging'); }));
uploadZone.addEventListener('drop', (event) => uploadFile(event.dataTransfer.files[0]));
$('above-water').addEventListener('change', updateControls);
$('camera-mode').addEventListener('change', updateMode);
$('confidence').addEventListener('input', () => { $('confidence-value').textContent = Number($('confidence').value).toFixed(2); });
$('analyze').addEventListener('click', startAnalysis);
$('cancel-job').addEventListener('click', async () => { if (!state.job) return; try { await api(`/api/jobs/${encodeURIComponent(state.job.id)}/cancel`, jsonOptions({})); toast('Đã gửi yêu cầu hủy.'); } catch (error) { showNotice(error.message, true); } });
$('draw-region').addEventListener('click', () => {
  if (state.drawing) {
    if (state.polygon.length < 3) { toast('Cần chọn ít nhất 3 đỉnh để tạo vùng nước.'); return; }
    stopDrawing();
    $('region-hint').textContent = `Đã chọn vùng nước ${state.polygon.length} đỉnh. Giả thuyết mất dấu chỉ áp dụng trong vùng này.`;
  } else {
    video.pause();
    state.polygon = [];
    state.drawing = true;
    $('video-stage').classList.add('drawing');
    $('draw-region').textContent = '✓ Hoàn tất vùng nước';
    $('region-hint').textContent = 'Chạm lần lượt ít nhất 3 đỉnh trên video rồi nhấn “Hoàn tất vùng nước”.';
    $('monitor').scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  updateControls();
  renderFrame(true);
});
$('clear-region').addEventListener('click', () => { state.polygon = []; stopDrawing(); $('region-hint').textContent = 'Chưa chọn vùng nước. Suy luận mất dấu trong nước sẽ không được bật.'; updateControls(); renderFrame(true); });
canvas.addEventListener('pointerdown', (event) => {
  if (!state.drawing) return;
  const bounds = canvas.getBoundingClientRect();
  const rect = contentRect();
  const x = (event.clientX - bounds.left - rect.x) / rect.width;
  const y = (event.clientY - bounds.top - rect.y) / rect.height;
  if (x < 0 || x > 1 || y < 0 || y > 1) return;
  if (state.polygon.length >= 20) { toast('Vùng nước hỗ trợ tối đa 20 đỉnh.'); return; }
  state.polygon.push([Number(x.toFixed(5)), Number(y.toFixed(5))]);
  updateControls();
  renderFrame(true);
});
$('review-mode').addEventListener('change', () => { state.eventSignature = ''; renderEvents(); updatePerformance(); });
$('event-list').addEventListener('click', async (event) => {
  const seek = event.target.closest('[data-seek]');
  if (seek) { seekVideo(Number(seek.dataset.seek)); $('monitor').scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
  const ack = event.target.closest('[data-ack]');
  if (!ack || !state.job) return;
  ack.disabled = true;
  try {
    await api(`/api/jobs/${encodeURIComponent(state.job.id)}/events/${encodeURIComponent(ack.dataset.ack)}/ack`, jsonOptions({ note: 'Người dùng xác nhận đã xem trên giao diện.' }));
    state.acked.add(ack.dataset.ack);
    const item = state.analysis.events.find((e) => String(e.id) === ack.dataset.ack);
    if (item) item.acknowledged = true;
    state.eventSignature = '';
    renderEvents();
    toast('Đã xác nhận đã xem. Việc xác nhận không kết luận tình huống đã an toàn.');
  } catch (error) { ack.disabled = false; showNotice(`Không lưu được xác nhận: ${error.message}`, true); }
});
$('enable-audio').addEventListener('click', async () => { if (state.audioEnabled) { state.audioEnabled = false; stopAlarms(); updateAudioUI(); } else if (await enableAudio()) toast('Đã bật âm báo cho các sự kiện mới khi phát video.'); });
$('test-audio').addEventListener('click', async () => { if (await enableAudio()) playAlarm(2); });
$('volume').addEventListener('input', () => { state.volume = Number($('volume').value) / 100; $('volume-value').textContent = `${Math.round(state.volume * 100)}%`; updateAudioUI(); });
$('banner-mute').addEventListener('click', () => { state.audioEnabled = false; stopAlarms(); updateAudioUI(); toast('Đã tắt âm. Cảnh báo hình ảnh và nhật ký vẫn được giữ.'); });
$('enable-notifications').addEventListener('click', async () => {
  if (!('Notification' in window) || !window.isSecureContext) return;
  if (state.notificationEnabled) { state.notificationEnabled = false; $('enable-notifications').textContent = 'Bật'; $('notification-state').textContent = 'Đã tắt trong ứng dụng'; return; }
  try {
    const permission = await Notification.requestPermission();
    state.notificationEnabled = permission === 'granted';
    $('notification-state').textContent = permission === 'granted' ? 'Đã bật khi trang đang mở' : permission === 'denied' ? 'Quyền đã bị từ chối' : 'Chưa được cấp quyền';
    $('enable-notifications').textContent = state.notificationEnabled ? 'Tắt' : 'Bật';
  } catch (_) { toast('Không thể yêu cầu thông báo trên trình duyệt này.'); }
});
$('enable-vibration').addEventListener('change', () => { if ($('enable-vibration').checked && typeof navigator.vibrate === 'function') { navigator.vibrate(80); toast('Đã thử rung. Chỉ bật tính năng này nếu thiết bị thực sự phản hồi.'); } });
video.addEventListener('loadedmetadata', () => { renderFrame(true); updateControls(); });
video.addEventListener('timeupdate', () => { enforceBuffer(); renderFrame(); });
video.addEventListener('seeking', () => {
  state.seeking = true;
  if (hasFrontier() && video.currentTime > playbackCeiling() + .01) {
    video.currentTime = playbackCeiling();
    const now = Date.now();
    if (now - state.lastSeekToast > 2500) { toast('Chỉ có thể tua trong phần AI đã phân tích. Video sẽ chờ kết quả mới.'); state.lastSeekToast = now; }
  }
  renderFrame(true);
});
video.addEventListener('seeked', () => { renderFrame(true); state.seeking = false; });
video.addEventListener('play', () => { if (isRealtime()) { state.playbackIntent = true; state.bufferPaused = false; video.playbackRate = 1; enforceBuffer(); } else $('playback-state').textContent = state.analysis ? 'Đang giám sát theo thời gian video' : 'Đang phát nguồn · chưa có kết quả AI'; renderFrame(true); });
video.addEventListener('pause', () => { stopAlarms(); if (isRealtime()) { if (!state.bufferPaused) state.playbackIntent = false; updateStreamStatus(); } else if (!activeJob()) $('playback-state').textContent = state.analysis ? 'Đã tạm dừng · cảnh báo âm thanh tạm dừng' : 'Đã tạm dừng nguồn video'; });
video.addEventListener('ratechange', () => { if (hasFrontier() && video.playbackRate !== 1) video.playbackRate = 1; });
video.addEventListener('ended', () => { stopAlarms(); $('playback-state').textContent = 'Đã phát hết video · có thể xem lại sự kiện'; });
video.addEventListener('error', () => { if (state.selected) showNotice('Trình duyệt chưa phát được định dạng video này. Thử video MP4 H.264 hoặc kiểm tra bản chuyển mã do máy chủ cung cấp.', true); });
window.addEventListener('resize', () => renderFrame(true));
if ('ResizeObserver' in window) new ResizeObserver(() => renderFrame(true)).observe($('video-wrap'));
function animationLoop(time) { if (!video.paused && time - state.lastRender > 60) { state.lastRender = time; enforceBuffer(); renderFrame(); } requestAnimationFrame(animationLoop); }
requestAnimationFrame(animationLoop);

async function initialize() {
  capabilityUI();
  await Promise.all([loadStatus(), loadVideos().catch((error) => showNotice(`Chưa tải được thư viện video: ${error.message}`, true)), loadJobs().catch((error) => showNotice(`Chưa tải được lịch sử: ${error.message}`, true))]);
  updateControls();
  setInterval(loadStatus, 20000);
}
initialize();
