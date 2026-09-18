'use strict';
const $ = id => document.getElementById(id);
const fields = ['order','source_file','start_time','end_time','duration_seconds','transcript','role','reason','risk_note'];
let clips = [], rejected = [], current = 0, history = [], project = '片段审核', media = new Map(), playing = false, dirty = false;
const video = $('video');
const clone = value => JSON.parse(JSON.stringify(value));
const fileName = value => value.replaceAll('\\','/').split('/').pop();
const round = value => Math.round(value * 1000) / 1000;
function notice(text, error = false, scope = 'global') { const target = scope === 'export' ? $('export-help') : scope === 'media' ? $('media-state') : scope === 'trim' ? $('trim-status') : $('status'); target.textContent = text; target.className = error ? 'error' : ''; }
function button(text, action, className = '') { const node = document.createElement('button'); node.type = 'button'; node.textContent = text; node.className = className; node.onclick = action; return node; }
function snapshot() { history.push(clone({clips, current})); if (history.length > 100) history.shift(); dirty = true; $('reviewed').checked = false; notice('时间线已更改，请重新核对后导出。',false,'export'); }
function selected() { return clips.filter(c => c.selected); }
function validClip(item) {
  const c = item.clip;
  if (!c || !['source_file','transcript','role','reason','risk_note'].every(k => typeof c[k] === 'string' && c[k].length <= 30000)) throw new Error('片段字段不完整，请重新生成 JSON。');
  if (typeof item.selected !== 'boolean' || !Number.isFinite(item.source_duration_seconds) || ![c.start_time,c.end_time,c.duration_seconds].every(Number.isFinite)) throw new Error('时间或选择状态无效。');
  if (!(c.start_time >= 0 && c.end_time > c.start_time && c.end_time <= item.source_duration_seconds && Math.abs(c.end_time - c.start_time - c.duration_seconds) < .02)) throw new Error('存在超出素材或颠倒的切点。');
  if (!c.source_file || !c.transcript.trim() || c.source_file.replaceAll('\\','/').split('/').includes('raw_duplicates_quarantine')) throw new Error('源文件或转写内容无效。');
}
function load(data, name) {
  let candidates;
  if (data.format === 'roughcut-review' && data.version === 1) candidates = data.candidates;
  else if (data.schema_version === '1.0' && data.status === 'ok' && data.mode === 'timeline_only') candidates = data.result?.candidates;
  else throw new Error('请选择 RoughCut 生成的 JSON 或保存的审核会话。');
  if (!Array.isArray(candidates) || candidates.length > 1000 || !candidates.length) throw new Error('未找到候选片段，先检查转写结果。');
  const next = [], failures = [];
  for (const item of candidates) {
    if (item.clip === null && typeof item.reason === 'string') { failures.push(item.reason); continue; }
    validClip(item); next.push(clone(item));
  }
  if (!next.length) throw new Error('所有片段均无法审核，请修正索引中的时间或转写内容。');
  if (dirty && !window.confirm('当前审核尚未保存。继续会替换当前草稿；取消后可先保存审核会话。')) { notice('已保留当前草稿，可先保存审核会话。'); return; }
  stop(); media.forEach(entry => URL.revokeObjectURL(entry.url)); media.clear();
  clips = next; rejected = failures; current = 0; history = []; project = name; dirty = false;
  notice('导出后按 README 使用 FFmpeg 生成视频。尚未渲染。',false,'export');
  $('reviewed').checked = false; $('welcome').hidden = true; $('workspace').hidden = false;
  render(); notice(`${name}已载入。选择片段试听，或调整初选。`);
}
function stop() { playing = false; video.pause(); $('play').textContent = '试听片段'; }
function select(index) { stop(); current = index; render(); if (matchMedia('(max-width:800px)').matches) { $('preview-pane').focus({preventScroll:true}); $('preview-pane').scrollIntoView({block:'start'}); } else $('clips').children[index].querySelector('.clip-main').focus({preventScroll:true}); }
$('back').onclick = () => { const target = $('clips').children[current].querySelector('.clip-main'); target.focus({preventScroll:true}); target.scrollIntoView({block:'center'}); };
function render() {
  $('project-name').textContent = project; $('undo').disabled = !history.length;
  const list = $('clips'); list.replaceChildren();
  clips.forEach((item, index) => {
    const c = item.clip, row = document.createElement('article'); row.className = `clip${index === current ? ' active' : ''}`; row.dataset.index = index;
    const check = document.createElement('input'); check.type = 'checkbox'; check.checked = item.selected; check.setAttribute('aria-label', `保留片段 ${index + 1}`);
    check.onchange = () => { snapshot(); item.selected = check.checked; render(); notice(item.selected ? '片段已加入时间线。' : '片段已移出，可随时恢复。'); $('clips').children[index].querySelector('input').focus(); };
    const content = button('', () => select(index), 'clip-main'); content.setAttribute('aria-label', `查看片段 ${index + 1}`); content.setAttribute('aria-pressed', index === current);
    const time = document.createElement('span'); time.className = 'clip-time'; time.textContent = `${index + 1} / ${c.start_time.toFixed(2)} — ${c.end_time.toFixed(2)} s`;
    const text = document.createElement('p'); text.textContent = c.transcript; content.append(time, text);
    const note = document.createElement('p'); note.className = 'clip-note'; note.textContent = item.selected ? fileName(c.source_file) : `未选：${item.reason}`; content.append(note);
    const controls = document.createElement('div'); controls.className = 'clip-move';
    for (const [label, delta] of [['上移',-1],['下移',1]]) {
      const move = button(label, () => { snapshot(); stop(); [clips[index],clips[index + delta]] = [clips[index + delta],clips[index]]; current = index + delta; render(); $('clips').children[current].querySelector('.clip-main').focus(); notice('片段顺序已调整。'); });
      move.disabled = index + delta < 0 || index + delta >= clips.length; move.setAttribute('aria-label', `${label}片段 ${index + 1}`); controls.append(move);
    }
    row.append(check, content, controls); list.append(row);
  });
  const c = clips[current].clip;
  notice('',false,'trim');
  $('source-name').textContent = c.source_file; $('clip-text').textContent = c.transcript; $('reason').textContent = clips[current].reason; $('risk').textContent = c.risk_note;
  $('start').value = c.start_time; $('end').value = c.end_time; $('start').max = clips[current].source_duration_seconds; $('end').max = clips[current].source_duration_seconds;
  const entry = media.get(c.source_file);
  if (entry) {
    if (video.getAttribute('src') !== entry.url) { stop(); video.src = entry.url; video.load(); }
    video.hidden = false; $('media-empty').hidden = true; $('play').disabled = !entry.ready;
    notice(entry.error || (entry.ready ? '源视频已关联，仅在本机播放。' : '正在读取源视频…'),Boolean(entry.error),'media');
  } else {
    stop(); video.removeAttribute('src'); video.load(); video.hidden = true; $('media-empty').hidden = false; $('play').disabled = true; notice('仅在当前页面读取，不上传。',false,'media');
  }
  $('rejected').hidden = !rejected.length; const ul = $('rejected').querySelector('ul'); ul.replaceChildren(); rejected.forEach(reason => { const li = document.createElement('li'); li.textContent = reason; ul.append(li); });
  const picked = selected(); $('total').textContent = `${picked.length} 个片段 / ${picked.reduce((n,x) => n + x.clip.duration_seconds, 0).toFixed(2)} 秒`;
  $('strip').replaceChildren(); picked.forEach((item, order) => { const index = clips.indexOf(item); const node = button('', () => { select(index); if (!matchMedia('(max-width:800px)').matches) $('clips').children[index].querySelector('.clip-main').focus(); }); node.setAttribute('aria-current', index === current); const title = document.createElement('span'); title.textContent = item.clip.transcript; node.append(`${order + 1} / ${item.clip.duration_seconds.toFixed(2)} s`, title); $('strip').append(node); });
  if (!picked.length) $('strip').textContent = '还没有保留片段，勾选后即可导出。';
  $('export').disabled = !picked.length || !$('reviewed').checked;
}
$('demo').onclick = async () => { try { $('demo').disabled = true; notice('正在读取示例…'); const response = await fetch('/example.json'); if (!response.ok) throw new Error(); load(await response.json(), '虚构示例'); } catch { notice('示例读取失败，可以重试或导入自己的 JSON。',true); } finally { $('demo').disabled = false; } };
$('import').onclick = () => $('import-file').click();
$('import-file').onchange = async e => { const file = e.target.files[0]; if (!file) return; try { if (file.size > 5_000_000) throw new Error('JSON 不能超过 5 MB。'); load(JSON.parse(await file.text()), '导入的审核'); } catch (error) { notice(error instanceof SyntaxError ? 'JSON 格式错误，原草稿已保留。' : `${error.message} 原草稿已保留。`,true); } e.target.value = ''; };
$('attach').onclick = () => $('media-file').click();
$('media-file').onchange = e => {
  const file = e.target.files[0]; if (!file || !clips.length) return;
  const source = clips[current].clip.source_file;
  if (file.name !== fileName(source)) { notice(`请选择与当前片段对应的 ${fileName(source)}。`,true,'media'); e.target.value = ''; return; }
  stop(); if (media.has(source)) URL.revokeObjectURL(media.get(source).url);
  media.set(source, {url:URL.createObjectURL(file), ready:false}); render(); e.target.value = '';
};
video.onloadedmetadata = () => {
  if (!clips.length) return; const source = clips[current].clip.source_file, entry = media.get(source);
  if (!entry || video.getAttribute('src') !== entry.url) return;
  if (!Number.isFinite(video.duration) || clips.some(item => item.clip.source_file === source && item.clip.end_time > video.duration + .05)) { entry.error = '源视频时长不匹配，请重新关联正确文件。原切点已保留。'; notice(entry.error,true,'media'); return; }
  entry.ready = true; $('play').disabled = false; $('media-state').textContent = '源视频已关联，仅在本机播放。'; video.currentTime = clips[current].clip.start_time;
};
video.onerror = () => { if (video.getAttribute('src')) { $('play').disabled = true; const entry = media.get(clips[current]?.clip.source_file); const message = '浏览器无法播放此文件，请重新关联 H.264/AAC MP4 或在本地播放器试听。'; if (entry) {entry.error = message; entry.ready = false;} notice(message,true,'media'); } };
$('play').onclick = async () => { if (playing) { stop(); return; } const c = clips[current].clip; video.currentTime = c.start_time; try { await video.play(); playing = true; $('play').textContent = '暂停试听'; } catch { notice('播放失败，请重新关联源视频。',true,'media'); } };
video.ontimeupdate = () => { if (playing && video.currentTime >= clips[current].clip.end_time) stop(); };
video.onended = stop;
$('trim').onsubmit = e => { e.preventDefault(); const start = Number($('start').value), end = Number($('end').value); const item = clips[current]; if (!(Number.isFinite(start) && Number.isFinite(end) && start >= 0 && end > start && end <= item.source_duration_seconds)) { notice('切点无效：入点应小于出点，且不能超出源视频。',true,'trim'); return; } snapshot(); stop(); Object.assign(item.clip,{start_time:round(start),end_time:round(end),duration_seconds:round(end-start)}); item.clip.risk_note = '用户已调整切点，请重新试听核对句首句尾。'; render(); notice('切点已更新。请试听确认，也可撤销。',false,'trim'); };
$('undo').onclick = () => { const previous = history.pop(); if (!previous) return; dirty = true; stop(); clips = previous.clips; current = previous.current; $('reviewed').checked = false; render(); notice('已撤销上一步。'); notice('时间线已更改，请重新核对后导出。',false,'export'); };
function download(name, text, type) { const url = URL.createObjectURL(new Blob([text],{type})); const a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
$('save').onclick = () => { download('roughcut-review.json',JSON.stringify({format:'roughcut-review',version:1,candidates:[...clips,...rejected.map(reason => ({clip:null,reason}))]},null,2),'application/json'); dirty = false; notice('审核会话已导出。下次导入可恢复选择，需重新关联视频。'); };
$('reviewed').onchange = () => { $('export').disabled = !selected().length || !$('reviewed').checked; };
$('export').onclick = () => { if (!$('reviewed').checked || !selected().length) return; selected().forEach(validClip); const rows = selected().map((item,index) => ({...item.clip,order:index + 1})); const quote = value => `"${String(value ?? '').replaceAll('"','""')}"`; const csv = [fields,...rows.map(row => fields.map(key => row[key]))].map(row => row.map(quote).join(',')).join('\r\n') + '\r\n'; download('timeline_review.csv',csv,'text/csv;charset=utf-8'); notice('审核时间线已导出，尚未生成视频。将文件放入 output 后运行渲染命令。',false,'export'); };
window.addEventListener('beforeunload', e => { if (dirty) { e.preventDefault(); e.returnValue = ''; } });
