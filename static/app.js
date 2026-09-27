const form = document.getElementById('captionForm');
const videoInput = document.getElementById('videoInput');
const dropzone = document.getElementById('dropzone');
const filePill = document.getElementById('filePill');
const submitBtn = document.getElementById('submitBtn');
const submitText = document.getElementById('submitText');
const spinner = document.getElementById('spinner');
const fontSize = document.getElementById('fontSize');
const fontSizeValue = document.getElementById('fontSizeValue');
const positionRange = document.getElementById('positionRange');
const positionValue = document.getElementById('positionValue');
const positionPreset = document.getElementById('positionPreset');
const hotwords = document.getElementById('hotwords');
const exportVolume = document.getElementById('exportVolume');
const exportVolumeValue = document.getElementById('exportVolumeValue');
const progressWrap = document.getElementById('progressWrap');
const progressTitle = document.getElementById('progressTitle');
const progressPercent = document.getElementById('progressPercent');
const progressBar = document.getElementById('progressBar');
const result = document.getElementById('result');
const resultVideo = document.getElementById('resultVideo');
const downloadBtn = document.getElementById('downloadBtn');
const startOverBtn = document.getElementById('startOverBtn');
const detectedLanguage = document.getElementById('detectedLanguage');
const errorBox = document.getElementById('errorBox');
const templateGrid = document.getElementById('templateGrid');
const sourcePreviewWrap = document.getElementById('sourcePreviewWrap');
const sourcePreview = document.getElementById('sourcePreview');
const sourceAudioBtn = document.getElementById('sourceAudioBtn');
const sourceVolume = document.getElementById('sourceVolume');
const sourceVolumeValue = document.getElementById('sourceVolumeValue');
const captionOverlay = document.getElementById('captionOverlay');
const resultAudioBtn = document.getElementById('resultAudioBtn');
const resultVolume = document.getElementById('resultVolume');
const resultVolumeValue = document.getElementById('resultVolumeValue');
const language = document.getElementById('language');

const captionEditor = document.getElementById('captionEditor');
const editorVideo = document.getElementById('editorVideo');
const editorCaptionOverlay = document.getElementById('editorCaptionOverlay');
const captionList = document.getElementById('captionList');
const editorStatus = document.getElementById('editorStatus');
const editorTime = document.getElementById('editorTime');
const editorPlayBtn = document.getElementById('editorPlayBtn');
const editorVolume = document.getElementById('editorVolume');
const editorVolumeValue = document.getElementById('editorVolumeValue');
const addCaptionBtn = document.getElementById('addCaptionBtn');
const resetCaptionsBtn = document.getElementById('resetCaptionsBtn');
const backToSettingsBtn = document.getElementById('backToSettingsBtn');
const renderEditedBtn = document.getElementById('renderEditedBtn');
const renderEditedText = document.getElementById('renderEditedText');
const renderSpinner = document.getElementById('renderSpinner');

let resultUrl = null;
let sourceUrl = null;
let selectedTemplate = 'bold_white';
let selectedTemplateObject = null;
let editorTemplateId = 'bold_white';
let editorTemplateObject = null;
let editorSessionId = null;
let editorChunks = [];
let originalEditorChunks = [];
let editorSourceUrl = null;
let activeCaptionId = null;
let lastOverlaySignature = "";
let currentAnimatedChunkId = null;

const TEMPLATE_VISUALS = {
  // These values mirror the original V6 template CSS. The editor uses the
  // original .t-* classes for the actual visual design; this map only controls
  // the responsive scale and active-word behavior.
  bold_white: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  white_yellow: {scale:1, twoTier:true, activeColor:'#ffe600', lineHeight:'.92'},
  yellow_glow: {scale:1, twoTier:false, activeColor:null, lineHeight:'.92'},
  creator_bold: {scale:1, twoTier:true, activeColor:'#ffd400', lineHeight:'.82'},
  clean_white: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  yellow_bold: {scale:1, twoTier:false, activeColor:null, lineHeight:'.92'},
  black_box: {scale:1, twoTier:true, activeColor:'#ffe600', lineHeight:'.92'},
  white_box: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  red_alert: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  cyan_pop: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  blue_electric: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  pink_creator: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  soft_aesthetic: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  typewriter: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  minimal_shadow: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  news_ticker: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  purple_neon: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  green_focus: {scale:1, twoTier:true, activeColor:null, lineHeight:'.92'},
  editing_skool: {scale:1, twoTier:true, activeColor:null, lineHeight:'.90'},
  mr_beast: {scale:1, twoTier:true, activeColor:null, lineHeight:'.88'},
  mr_beast_gold: {scale:1, twoTier:true, activeColor:null, lineHeight:'.88'},
  highlight_orange: {scale:1, twoTier:false, activeColor:'#ff9d00', lineHeight:'.92'},
  green_glow: {scale:1, twoTier:false, activeColor:null, lineHeight:'.90'},
  big_reveal: {scale:1, twoTier:false, activeColor:null, lineHeight:'.86'},
  deep_shadow: {scale:1, twoTier:true, activeColor:null, lineHeight:'.90'},
  aqua_pop: {scale:1, twoTier:false, activeColor:null, lineHeight:'.90'},
  red_black_punch: {scale:1, twoTier:false, activeColor:null, lineHeight:'.90'}
};

function applyTemplateWordStyle(el, templateId, active=false) {
  // IMPORTANT: do not assign font/color/background/size here. The actual
  // template's .t-* selector must remain the single source of truth.
  el.className = `tracked-word${active ? ' word-active' : ''}`;
  el.style.textDecoration = 'none';
  el.style.textDecorationLine = 'none';
  el.style.borderBottom = '0';
  el.style.boxShadow = 'none';
}

function applyTemplateOverlayStyle(overlay, templateId) {
  const v = TEMPLATE_VISUALS[templateId] || TEMPLATE_VISUALS.bold_white;
  overlay.style.display = 'block';
  overlay.style.textAlign = 'center';
  overlay.style.whiteSpace = 'normal';
  overlay.style.lineHeight = v.lineHeight || '0.92';
  overlay.style.textDecoration = 'none';
  overlay.style.textDecorationLine = 'none';
  overlay.style.maxWidth = '92%';
  overlay.style.boxSizing = 'border-box';
  overlay.style.overflow = 'hidden';
}

function splitWordsForTemplate(words, maxWords=6, maxChars=34) {
  const clean = (words || []).filter(w => String(w?.text || '').trim());
  const groups = [];
  let current = [];
  for (const word of clean) {
    const candidate = current.concat([word]);
    const chars = candidate.map(w => String(w.text || '').trim()).join(' ').length;
    if (current.length && (candidate.length > maxWords || chars > maxChars)) {
      groups.push(current);
      current = [word];
    } else {
      current = candidate;
    }
  }
  if (current.length) groups.push(current);
  return groups.length ? groups : [[]];
}

function templateWordMarkup(group, startIndex, activeIndex, tagName='strong') {
  const open = '<div class="caption-line">';
  const close = '</div>';
  return open + group.map((w, i) => {
    const idx = startIndex + i;
    const active = idx === activeIndex;
    return `<${tagName} class="tracked-word${active ? ' word-active' : ''}" data-word-index="${idx}">${esc(w.text)}</${tagName}>`;
  }).join(' ') + close;
}

function formatCaptionLinesJS(words, template) {
  const clean = (words || []).map(w => typeof w === 'string' ? w : (w?.text || '')).map(s => String(s).trim()).filter(Boolean);
  if (!clean.length) return '';
  const maxLines = Number(template?.max_lines || 2);
  if (maxLines === 1 || clean.length <= 1) return clean.join(' ');
  const wpl = (template?.words_per_line && Array.isArray(template.words_per_line) && template.words_per_line.length)
    ? template.words_per_line
    : (clean.length === 3 ? [2, 1] : [Math.max(1, Math.floor(clean.length / 2)), Math.max(1, clean.length - Math.floor(clean.length / 2))]);

  const lines = [];
  let idx = 0;
  for (let i = 0; i < wpl.length; i++) {
    if (idx >= clean.length) break;
    const count = wpl[i];
    if (i === wpl.length - 1) {
      lines.push(clean.slice(idx).join(' '));
      idx = clean.length;
    } else {
      const remainingLines = wpl.length - (i + 1);
      let take = Math.min(count, clean.length - idx);
      if ((clean.length - (idx + take)) < remainingLines) {
        take = Math.max(1, clean.length - idx - remainingLines);
      }
      lines.push(clean.slice(idx, idx + take).join(' '));
      idx += take;
    }
  }
  if (idx < clean.length) {
    if (lines.length) lines[lines.length - 1] += ' ' + clean.slice(idx).join(' ');
    else lines.push(clean.slice(idx).join(' '));
  }
  return lines.join('\n');
}

function partitionWordsJS(words, template, explicitText = '') {
  const list = (words || []).slice();
  if (!list.length) return [];
  const maxLines = Number(template?.max_lines || 2);
  if (maxLines === 1 || list.length <= 1) return [list];

  const rawText = String(explicitText || '').trim();
  if (rawText.includes('\n')) {
    const textLines = rawText.split('\n').map(l => l.trim()).filter(Boolean);
    if (textLines.length > 1) {
      const groups = [];
      let wIdx = 0;
      for (let i = 0; i < textLines.length; i++) {
        const count = textLines[i].split(/\s+/).filter(Boolean).length;
        if (i === textLines.length - 1) {
          groups.push(list.slice(wIdx));
          wIdx = list.length;
        } else {
          const remaining = textLines.length - (i + 1);
          let take = Math.min(count, list.length - wIdx);
          if ((list.length - (wIdx + take)) < remaining) {
            take = Math.max(1, list.length - wIdx - remaining);
          }
          groups.push(list.slice(wIdx, wIdx + take));
          wIdx += take;
        }
      }
      if (wIdx < list.length) {
        if (groups.length) groups[groups.length - 1].push(...list.slice(wIdx));
        else groups.push(list.slice(wIdx));
      }
      return groups.filter(g => g.length > 0);
    }
  }

  const wpl = (template?.words_per_line && Array.isArray(template.words_per_line) && template.words_per_line.length)
    ? template.words_per_line
    : (list.length === 3 ? [2, 1] : [Math.max(1, Math.floor(list.length / 2)), Math.max(1, list.length - Math.floor(list.length / 2))]);

  const groups = [];
  let wIdx = 0;
  for (let i = 0; i < wpl.length; i++) {
    if (wIdx >= list.length) break;
    const count = wpl[i];
    if (i === wpl.length - 1) {
      groups.push(list.slice(wIdx));
      wIdx = list.length;
    } else {
      const remaining = wpl.length - (i + 1);
      let take = Math.min(count, list.length - wIdx);
      if ((list.length - (wIdx + take)) < remaining) {
        take = Math.max(1, list.length - wIdx - remaining);
      }
      groups.push(list.slice(wIdx, wIdx + take));
      wIdx += take;
    }
  }
  if (wIdx < list.length) {
    if (groups.length) groups[groups.length - 1].push(...list.slice(wIdx));
    else groups.push(list.slice(wIdx));
  }
  return groups.filter(g => g.length > 0);
}

const templates = [
  {id:'bold_white', name:'Bold White', tag:'Oversized', a:'MAKE IT', b:'BOLD', cls:'t-bold-white'},
  {id:'white_yellow', name:'White + Yellow', tag:'Creator', a:'THIS IS', b:'IMPORTANT', cls:'t-white-yellow'},
  {id:'yellow_glow', name:'Yellow Glow', tag:'Glow', a:'CAPTIONS', b:'', cls:'t-yellow-glow'},
  {id:'creator_bold', name:'Creator Bold', tag:'Big text', a:'UNIQUE', b:'BOLD', cls:'t-creator-bold'},
  {id:'clean_white', name:'Clean White', tag:'Minimal', a:'simple', b:'captions', cls:'t-clean'},
  {id:'yellow_bold', name:'Yellow Bold', tag:'High contrast', a:'INSTAGRAM', b:'', cls:'t-yellow-bold'},
  {id:'black_box', name:'Black Box', tag:'Readable', a:'READABLE', b:'ANYWHERE', cls:'t-black-box'},
  {id:'white_box', name:'White Box', tag:'Modern', a:'CLEAN', b:'CARD', cls:'t-white-box'},
  {id:'red_alert', name:'Red Alert', tag:'Punchy', a:'STOP', b:'SCROLLING', cls:'t-red-alert'},
  {id:'cyan_pop', name:'Cyan Pop', tag:'Neon', a:'WATCH', b:'THIS', cls:'t-cyan'},
  {id:'blue_electric', name:'Blue Electric', tag:'Tech', a:'LEVEL UP', b:'NOW', cls:'t-blue'},
  {id:'pink_creator', name:'Pink Creator', tag:'Social', a:'MAKE', b:'CONTENT', cls:'t-pink'},
  {id:'soft_aesthetic', name:'Soft Aesthetic', tag:'Vlog', a:'a little', b:'different', cls:'t-aesthetic'},
  {id:'typewriter', name:'Typewriter', tag:'Story', a:'TELL THE', b:'STORY', cls:'t-typewriter'},
  {id:'cream_retro', name:'Cream Retro', tag:'Retro', a:'A LITTLE', b:'RETRO', cls:'t-cream-retro'},
  {id:'minimal_shadow', name:'Minimal Shadow', tag:'Clean', a:'SAY IT', b:'CLEARLY', cls:'t-minimal'},
  {id:'news_ticker', name:'News Ticker', tag:'Headline', a:'BREAKING', b:'NEWS', cls:'t-news'},
  {id:'purple_neon', name:'Purple Neon', tag:'Night', a:'CREATE', b:'MORE', cls:'t-purple'},
  {id:'green_focus', name:'Green Focus', tag:'Energy', a:'FOCUS', b:'HERE', cls:'t-green'},
  {id:'editing_skool', name:'Editing Skool', tag:'Creator', a:'MAKE IT', b:'POP', cls:'t-editing-skool'},
  {id:'mr_beast', name:'Mr Beast Style', tag:'Bold', a:'THE', b:'MOMENT', cls:'t-mr-beast'},
  {id:'mr_beast_gold', name:'Mr Beast Gold', tag:'Bold', a:'THIS IS', b:'BIG', cls:'t-mr-beast-gold'},
  {id:'highlight_orange', name:'Highlighted Word', tag:'Dynamic', a:'WATCH', b:'THIS', cls:'t-highlight-orange'},
  {id:'green_glow', name:'Creator Glow', tag:'Glow', a:'GO', b:'VIRAL', cls:'t-green-glow'},
  {id:'big_reveal', name:'Big Reveal', tag:'Kinetic', a:'THIS', b:'CHANGES', cls:'t-big-reveal'},
  {id:'deep_shadow', name:'Deep Shadow', tag:'Clean', a:'THE', b:'ANSWER', cls:'t-deep-shadow'},
  {id:'aqua_pop', name:'Aqua Pop', tag:'Neon', a:'LEVEL', b:'UP', cls:'t-aqua-pop'},
  {id:'red_black_punch', name:'Red Punch', tag:'Punchy', a:'STOP', b:'NOW', cls:'t-red-black-punch'},
  {id:'clean_glow', name:'Clean Glow', tag:'Minimal', a:'the quick', b:'brown fox', cls:'t-clean-glow'},
  {id:'pixelated_word', name:'Pixelated Word', tag:'Word', a:'THE', b:'BROWN', cls:'t-pixelated'},
  {id:'liquid_glass', name:'Liquid Glass', tag:'Glass', a:'the quick', b:'fox', cls:'t-liquid-glass'},
  {id:'tabahi', name:'Tabahi', tag:'Editorial', a:'THE QUICK', b:'BROWN FOX', cls:'t-tabahi'},
  {id:'deep_glow', name:'Deep Glow', tag:'Glow', a:'BROWN FOX', b:'JUMPS OVER', cls:'t-deep-glow'},
  {id:'highlighted_word', name:'Highlighted Word', tag:'Dynamic', a:'the', b:'quick fox', cls:'t-highlighted-word'},
  {id:'delhi_editor', name:'Delhi', tag:'Editorial', a:'the quick', b:'brown fox', cls:'t-delhi'},
  {id:'aura_blue', name:'Aura', tag:'Editorial', a:'forget', b:'STATUS', cls:'t-aura-blue'},
  {id:'swiss_focus', name:'Swiss', tag:'Editorial', a:'focus', b:'DEEPLY', cls:'t-swiss'},
  {id:'scribble', name:'Scribble', tag:'Handwritten', a:'the little', b:'things', cls:'t-scribble'}
];

function templateById(id) { return templates.find(t => t.id === id) || templates[0]; }

function mergeServerTemplates(serverTemplates) {
  if (!Array.isArray(serverTemplates) || !serverTemplates.length) return;
  const byId = new Map(templates.map(t => [t.id, t]));
  serverTemplates.forEach(st => {
    if (byId.has(st.id)) {
      Object.assign(byId.get(st.id), st);
    } else {
      templates.push(st);
    }
  });
  selectedTemplateObject = templateById(selectedTemplate);
  renderTemplates();
  applyPreviewTemplate();
  if (!captionEditor.hidden) updateEditorOverlay();
}

async function loadTemplateContract() {
  try {
    const r = await fetch('/api/templates');
    if (!r.ok) return;
    const data = await r.json();
    mergeServerTemplates(data.templates);
  } catch (_) {}
}

function renderTemplates() {
  const query = (document.getElementById('templateSearch')?.value || '').trim().toLowerCase();
  const category = document.querySelector('.template-filter.active')?.dataset.category || 'all';
  const visible = templates.filter(t => {
    const matchesCategory = category === 'all' || t.category === category;
    const hay = `${t.name || ''} ${t.tag || ''} ${t.category || ''} ${t.id || ''}`.toLowerCase();
    return matchesCategory && (!query || hay.includes(query));
  });
  templateGrid.innerHTML = visible.map(t => `
    <label class="template-card ${t.id === selectedTemplate ? 'selected' : ''}">
      <input type="radio" name="template" value="${t.id}" ${t.id === selectedTemplate ? 'checked' : ''}>
      <div class="template-preview ${t.css_class || t.cls || ''}">
        <span>${t.preview_a || t.a || 'CAPTION'}</span>
        ${t.preview_b || t.b ? `<strong>${t.preview_b || t.b}</strong>` : ''}
        <small class="template-chip">${t.category || 'Creator'}</small>
      </div>
      <div class="template-meta"><strong>${t.name || t.id}</strong><span>${t.tag || 'Creator'}</span></div>
    </label>
  `).join('') || `<div class="template-empty">No templates match your search.</div>`;

  const lockedNameEl = document.getElementById('editorLockedTemplateName');
  if (lockedNameEl) {
    const currentTmpl = templateById(editorTemplateId || selectedTemplate);
    lockedNameEl.textContent = currentTmpl?.name || editorTemplateId || selectedTemplate;
  }
}

templateGrid.addEventListener('change', event => {
  if (event.target.name !== 'template') return;
  // If caption editor is active, template is strictly locked
  if (!captionEditor.hidden) return;
  selectedTemplate = event.target.value;
  selectedTemplateObject = templateById(selectedTemplate);
  document.querySelectorAll('.template-card').forEach(card => card.classList.remove('selected'));
  event.target.closest('.template-card').classList.add('selected');
  const tmplPos = selectedTemplateObject?.position || 'lower';
  positionRange.value = tmplPos === 'center' ? 50 : (tmplPos === 'top' ? 18 : 78);
  positionValue.textContent = `${positionRange.value}%`;
  const posRange = document.getElementById('editorPosRange');
  const posVal = document.getElementById('editorPosVal');
  if (posRange) posRange.value = positionRange.value;
  if (posVal) posVal.textContent = `${positionRange.value}%`;
  applyPreviewTemplate();
  applyPreviewPosition();
});

document.getElementById('templateSearch')?.addEventListener('input', renderTemplates);
document.querySelectorAll('.template-filter').forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('.template-filter').forEach(x => x.classList.remove('active'));
  btn.classList.add('active');
  renderTemplates();
}));

function formatBytes(bytes) {
  const units = ['B','KB','MB','GB'];
  let size = bytes;
  let i = 0;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function makeVideoBlobUrl(file) {
  if (!file) return null;
  let mime = file.type;
  if (!mime || !mime.startsWith('video/')) {
    const ext = (file.name || '').split('.').pop().toLowerCase();
    const map = {
      mp4: 'video/mp4',
      m4v: 'video/mp4',
      mov: 'video/quicktime',
      webm: 'video/webm',
      ogv: 'video/ogg',
      mkv: 'video/mp4',
      avi: 'video/x-msvideo'
    };
    mime = map[ext] || 'video/mp4';
  }
  try {
    const typedBlob = file.slice(0, file.size, mime);
    return URL.createObjectURL(typedBlob);
  } catch (_) {
    return URL.createObjectURL(file);
  }
}

function setupVideoAudioSync(video, volumeInput, volumeLabel, audioBtn, defaultBtnText='Play with audio') {
  if (!video) return;

  const updateUI = () => {
    const isMuted = video.muted || video.volume === 0;
    const volPercent = isMuted ? 0 : Math.round(video.volume * 100);
    if (volumeInput) volumeInput.value = isMuted && video.volume > 0 ? 0 : volPercent;
    if (volumeLabel) volumeLabel.textContent = isMuted ? (video.muted ? 'Muted' : '0%') : `${volPercent}%`;
    if (audioBtn) {
      if (video.paused) {
        audioBtn.textContent = isMuted ? 'Unmute & Play' : defaultBtnText;
      } else {
        audioBtn.textContent = isMuted ? 'Unmute' : 'Pause audio';
      }
    }
  };

  const ensureSound = () => {
    video.defaultMuted = false;
    video.muted = false;
    const targetVol = volumeInput ? Number(volumeInput.value) / 100 : 1.0;
    video.volume = Math.max(0.05, Math.min(1.0, isNaN(targetVol) || targetVol <= 0 ? 1.0 : targetVol));
    if (volumeInput && Number(volumeInput.value) <= 0) {
      volumeInput.value = 100;
    }
    updateUI();
  };

  video.addEventListener('volumechange', updateUI);
  video.addEventListener('play', () => {
    if (video.muted) {
      video.muted = false;
    }
    updateUI();
  });
  video.addEventListener('pause', updateUI);
  video.addEventListener('loadedmetadata', () => {
    video.defaultMuted = false;
    video.muted = false;
    if (volumeInput) {
      const v = Number(volumeInput.value);
      video.volume = (isNaN(v) || v <= 0) ? 1.0 : (v / 100);
    } else {
      video.volume = 1.0;
    }
    updateUI();
  });

  if (volumeInput) {
    volumeInput.addEventListener('input', () => {
      const val = Number(volumeInput.value);
      if (val === 0) {
        video.muted = true;
      } else {
        video.muted = false;
        video.volume = Math.max(0.01, Math.min(1.0, val / 100));
      }
      updateUI();
    });
  }

  if (audioBtn) {
    audioBtn.addEventListener('click', async () => {
      ensureSound();
      try {
        if (video.paused) {
          await video.play();
        } else {
          video.pause();
        }
      } catch (err) {
        console.warn('Playback error:', err);
      }
      updateUI();
    });
  }
}

function selectFile(file) {
  if (!file) return;
  const ext = (file.name || '').split('.').pop().toLowerCase();
  const validExts = ['mp4','mov','m4v','webm','mkv','avi','ts','flv','3gp','wmv'];
  if (!file.type.startsWith('video/') && !validExts.includes(ext)) {
    showError('Please choose a valid video file.');
    return;
  }
  const dt = new DataTransfer();
  dt.items.add(file);
  videoInput.files = dt.files;
  filePill.textContent = `${file.name} · ${formatBytes(file.size)}`;
  filePill.hidden = false;
  submitBtn.disabled = false;
  hideError();

  if (sourceUrl) URL.revokeObjectURL(sourceUrl);
  sourceUrl = makeVideoBlobUrl(file);
  sourcePreview.src = sourceUrl;
  sourcePreview.defaultMuted = false;
  sourcePreview.muted = false;
  const vol = Number(sourceVolume?.value || 100) / 100;
  sourcePreview.volume = Math.max(0.05, isNaN(vol) ? 1.0 : vol);
  sourcePreview.setAttribute('preload', 'auto');
  sourcePreview.load();
  sourcePreviewWrap.hidden = false;
  sourceAudioBtn.textContent = 'Play with audio';
}

videoInput.addEventListener('change', () => selectFile(videoInput.files[0]));

// Use one explicit picker path. This avoids the double-label/click behavior
// that could make the first file selection appear to do nothing.
dropzone.addEventListener('click', event => {
  if (event.target === videoInput) return;
  videoInput.value = '';
  videoInput.click();
});
dropzone.addEventListener('keydown', event => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    videoInput.value = '';
    videoInput.click();
  }
});
['dragenter','dragover'].forEach(name => dropzone.addEventListener(name, e => {
  e.preventDefault();
  dropzone.classList.add('dragging');
}));
['dragleave','drop'].forEach(name => dropzone.addEventListener(name, e => {
  e.preventDefault();
  dropzone.classList.remove('dragging');
}));
dropzone.addEventListener('drop', e => selectFile(e.dataTransfer.files[0]));

setupVideoAudioSync(sourcePreview, sourceVolume, sourceVolumeValue, sourceAudioBtn, 'Play with audio');
setupVideoAudioSync(resultVideo, resultVolume, resultVolumeValue, resultAudioBtn, 'Play with audio');

fontSize.addEventListener('input', () => {
  fontSizeValue.textContent = fontSize.value;
  applyPreviewTemplate();
});

positionRange.addEventListener('input', () => {
  positionValue.textContent = `${positionRange.value}%`;
  applyPreviewPosition();
});

positionPreset.addEventListener('change', () => {
  const values = {top: 16, upper: 32, center: 50, lower: 68, bottom: 84};
  positionRange.value = values[positionPreset.value] ?? 78;
  positionValue.textContent = `${positionRange.value}%`;
  applyPreviewPosition();
});

function applyPreviewPosition() {
  captionOverlay.style.top = `${positionRange.value}%`;
  captionOverlay.style.transform = 'translate(-50%, -50%)';
}

function applyPreviewTemplate() {
  const template = templateById(selectedTemplate);
  selectedTemplateObject = template;
  captionOverlay.className = `caption-overlay ${template.css_class || template.cls || ''}`;
  if (template.max_lines === 1 || Number(template.span_scale || 0.65) >= 0.95) {
    captionOverlay.classList.add('single-tier');
  } else {
    captionOverlay.classList.remove('single-tier');
  }
  const previewA = template.preview_a || template.a || 'CAPTION';
  const previewB = template.preview_b || template.b || '';
  captionOverlay.innerHTML = `<span>${esc(previewA)}</span>${previewB ? `<strong>${esc(previewB)}</strong>` : ''}`;
  const basePx = Math.max(16, Math.round(Number(template.font_size || 52) * 0.5 * (Number(fontSize.value || 54) / 54.0)));
  captionOverlay.style.setProperty('--caption-font-size', `${basePx}px`);
  captionOverlay.style.setProperty('--span-scale', template.span_scale || (template.max_lines === 1 ? '1.0' : '0.65'));
}

form.addEventListener('submit', event => {
  event.preventDefault();
  const file = videoInput.files[0];
  if (!file) return;

  hideError();
  result.hidden = true;
  progressWrap.hidden = false;
  submitBtn.disabled = true;
  submitText.textContent = 'Transcribing…';
  spinner.hidden = false;
  progressTitle.textContent = 'Uploading video…';
  progressPercent.textContent = '0%';
  progressBar.style.width = '0%';

  const data = new FormData();
  data.append('video', file);
  data.append('language', language.value);
  data.append('position', 'bottom');
  data.append('position_percent', positionRange.value);
  data.append('font_size', fontSize.value);
  data.append('template', selectedTemplate);
  data.append('audio_volume', exportVolume.value);
  data.append('hotwords', hotwords.value.trim());

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/caption');
  xhr.responseType = 'json';
  xhr.upload.onprogress = e => {
    if (!e.lengthComputable) return;
    const pct = Math.round((e.loaded / e.total) * 100);
    progressPercent.textContent = `${pct}%`;
    progressBar.style.width = `${pct}%`;
    if (pct >= 100) {
      progressTitle.textContent = 'AI is transcribing your captions…';
      progressPercent.textContent = 'Working';
    }
  };
  xhr.onload = () => {
    spinner.hidden = true;
    submitText.textContent = 'Generate captions';
    if (xhr.status >= 200 && xhr.status < 300 && xhr.response) {
      openCaptionEditor(xhr.response);
    } else {
      showError((xhr.response && xhr.response.detail) || 'Something went wrong while transcribing the video.');
      resetProcessingState();
    }
  };
  xhr.onerror = () => {
    showError('Network error. Make sure the server is running and try again.');
    resetProcessingState();
  };
  xhr.send(data);
});

function cloneChunks(chunks) {
  return JSON.parse(JSON.stringify(chunks || []));
}
function fmtTime(seconds) {
  const s = Math.max(0, Number(seconds) || 0);
  const mins = Math.floor(s / 60);
  const secs = s - mins * 60;
  return `${String(mins).padStart(2,'0')}:${secs.toFixed(1).padStart(4,'0')}`;
}
function esc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
}
function getChunkById(id) { return editorChunks.find(c => c.id === id); }
function renumberChunks() { editorChunks.forEach((c, i) => c.id = i + 1); }
function syncTemplateSelectionUI() {
  document.querySelectorAll('input[name="template"]').forEach(input => {
    const selected = input.value === selectedTemplate;
    input.checked = selected;
    const card = input.closest('.template-card');
    if (card) card.classList.toggle('selected', selected);
  });
}

function openCaptionEditor(data) {
  editorSessionId = data.session_id;
  selectedTemplate = (data.template && data.template.id) || data.template || selectedTemplate;
  selectedTemplateObject = (typeof data.template === 'object' ? data.template : templateById(selectedTemplate));
  editorTemplateId = selectedTemplate;
  editorTemplateObject = selectedTemplateObject;
  editorChunks = cloneChunks(data.chunks).map(c => ({
    ...c,
    template_id: editorTemplateId,
    template: editorTemplateObject
  }));
  originalEditorChunks = cloneChunks(editorChunks);
  syncTemplateSelectionUI();
  fontSize.value = data.font_size || fontSize.value;
  fontSizeValue.textContent = fontSize.value;
  positionRange.value = data.position_percent || positionRange.value;
  positionValue.textContent = `${positionRange.value}%`;
  exportVolume.value = data.audio_volume ?? exportVolume.value;
  exportVolumeValue.textContent = `${exportVolume.value}%`;
  const lockedNameEl = document.getElementById('editorLockedTemplateName');
  if (lockedNameEl) {
    lockedNameEl.textContent = selectedTemplateObject?.name || selectedTemplate;
  }
  const editorFSRange = document.getElementById('editorFontSizeRange');
  const editorFSVal = document.getElementById('editorFontSizeVal');
  if (editorFSRange) editorFSRange.value = fontSize.value;
  if (editorFSVal) editorFSVal.textContent = `${fontSize.value}px`;
  const editorPRange = document.getElementById('editorPosRange');
  const editorPVal = document.getElementById('editorPosVal');
  if (editorPRange) editorPRange.value = positionRange.value;
  if (editorPVal) editorPVal.textContent = `${positionRange.value}%`;
  if (sourcePreview) {
    try { sourcePreview.pause(); } catch (_) {}
    sourcePreview.removeAttribute('src');
    sourcePreview.load();
  }
  editorSourceUrl = data.source_url;
  const editorFile = (videoInput.files && videoInput.files[0]);
  editorVideo.src = editorFile ? makeVideoBlobUrl(editorFile) : (sourceUrl || editorSourceUrl);
  editorVideo.defaultMuted = false;
  editorVideo.muted = false;
  const ev = Number(editorVolume?.value || 100) / 100;
  editorVideo.volume = Math.max(0.05, isNaN(ev) ? 1.0 : ev);
  editorVideo.load();
  form.hidden = true;
  progressWrap.hidden = true;
  result.hidden = true;
  captionEditor.hidden = false;
  editorStatus.textContent = `${editorChunks.length} captions`;
  currentAnimatedChunkId = null;
  renderCaptionRows();
  updateEditorOverlay();
  hideError();
  window.scrollTo({top: captionEditor.offsetTop - 20, behavior:'smooth'});
}
function renderCaptionRows() {
  editorStatus.textContent = `${editorChunks.length} caption${editorChunks.length === 1 ? '' : 's'}`;
  captionList.innerHTML = editorChunks.map((c, index) => {
    const words = Array.isArray(c.words) ? c.words : [];
    return `
    <article class="caption-row ${activeCaptionId === c.id ? 'active' : ''}" data-id="${c.id}">
      <button class="caption-jump" type="button" title="Jump to this caption">${index + 1}</button>
      <div class="caption-edit-main">
        <div class="caption-row-label">Caption text <span>• word timing is preserved when you correct words</span></div>
        <textarea class="caption-text" rows="2" spellcheck="false">${esc(c.text)}</textarea>
        <div class="word-tracking-strip">${words.map((w,wi)=>`<button type="button" class="word-chip" data-word-index="${wi}" title="Jump to ${fmtTime(w.start)}">${esc(w.text)}</button>`).join('')}</div>
        <div class="caption-time-grid">
          <label>Start <input class="caption-start" type="number" min="0" step="0.01" value="${Number(c.start).toFixed(2)}"></label>
          <label>End <input class="caption-end" type="number" min="0.05" step="0.01" value="${Number(c.end).toFixed(2)}"></label>
          <span class="caption-duration">${fmtTime(c.end-c.start)}</span>
        </div>
      </div>
      <button class="delete-caption" type="button" title="Delete caption">×</button>
    </article>`;
  }).join('');
}
function rebuildWordsPreservingTracking(oldWords, newWords, start, end) {
  const words = (newWords || []).filter(Boolean);
  if (!words.length) return [];
  const old = Array.isArray(oldWords) ? oldWords : [];
  const duration = Math.max(0.05, Number(end) - Number(start));

  // Normal correction: same number of words => preserve every original
  // Whisper boundary exactly. Only the displayed text changes.
  if (old.length === words.length && old.length) {
    const oldStart = Number(old[0].start);
    const oldEnd = Number(old[old.length - 1].end);
    const oldDuration = Math.max(0.001, oldEnd - oldStart);
    return words.map((text, i) => {
      const os = Number(old[i].start);
      const oe = Number(old[i].end);
      const rs = Math.max(0, Math.min(1, (os - oldStart) / oldDuration));
      const re = Math.max(rs, Math.min(1, (oe - oldStart) / oldDuration));
      return {
        text,
        start: Number(start) + rs * duration,
        end: Number(start) + re * duration,
      };
    });
  }

  // If the user adds/removes words, distribute timing only inside this
  // caption. Never borrow timing from the next caption chunk.
  const per = duration / words.length;
  return words.map((text, i) => ({
    text,
    start: Number(start) + i * per,
    end: Number(start) + (i + 1) * per,
  }));
}

function updateChunkFromRow(row) {
  const id = Number(row.dataset.id);
  const c = getChunkById(id);
  if (!c) return;
  activeCaptionId = c.id;
  const rawVal = row.querySelector('.caption-text').value;
  const lines = rawVal.split('\n').map(l => l.replace(/[^\S\r\n]+/g, ' ').trim()).filter(Boolean);
  const text = lines.join('\n');
  const start = Math.max(0, Number(row.querySelector('.caption-start').value) || 0);
  const end = Math.max(start + 0.05, Number(row.querySelector('.caption-end').value) || start + 0.5);
  const words = text.split(/\s+/).filter(Boolean);
  c.text = text;
  c.start = start;
  c.end = end;
  c.words = rebuildWordsPreservingTracking(c.words, words, start, end);
  c.template_id = editorTemplateId || selectedTemplate;
  c.template = editorTemplateObject || selectedTemplateObject;
  const dur = row.querySelector('.caption-duration');
  if (dur) dur.textContent = fmtTime(end-start);

  const strip = row.querySelector('.word-tracking-strip');
  if (strip && Array.isArray(c.words)) {
    strip.innerHTML = c.words.map((w, wi) =>
      `<button type="button" class="word-chip" data-word-index="${wi}" title="Jump to ${fmtTime(w.start)}">${esc(w.text)}</button>`
    ).join('');
  }

  if (editorVideo.paused) {
    editorVideo.currentTime = start;
  }
  updateEditorOverlay();
}
captionList.addEventListener('click', e => {
  const row = e.target.closest('.caption-row');
  if (!row) return;
  const c = getChunkById(Number(row.dataset.id));
  if (!c) return;
  if (e.target.closest('.caption-jump')) {
    activeCaptionId = c.id;
    editorVideo.currentTime = c.start;
    editorVideo.pause();
    renderCaptionRows();
    updateEditorOverlay();
  } else if (e.target.closest('.delete-caption')) {
    editorChunks = editorChunks.filter(x => x.id !== c.id);
    renumberChunks();
    activeCaptionId = null;
    renderCaptionRows();
    updateEditorOverlay();
  }
});
captionList.addEventListener('click', e => {
  const chip = e.target.closest('.word-chip');
  if (!chip) return;
  const row = e.target.closest('.caption-row');
  const c = row ? getChunkById(Number(row.dataset.id)) : null;
  const wi = Number(chip.dataset.wordIndex);
  if (!c || !c.words?.[wi]) return;
  activeCaptionId = c.id;
  editorVideo.currentTime = Number(c.words[wi].start);
  editorVideo.pause();
  renderCaptionRows();
  updateEditorOverlay();
});
captionList.addEventListener('input', e => {
  const row = e.target.closest('.caption-row');
  if (row && (e.target.classList.contains('caption-text') || e.target.classList.contains('caption-start') || e.target.classList.contains('caption-end'))) updateChunkFromRow(row);
});
captionList.addEventListener('focusin', e => {
  const row = e.target.closest('.caption-row');
  if (!row) return;
  activeCaptionId = Number(row.dataset.id);
  updateEditorOverlay();
});
editorVideo.addEventListener('timeupdate', () => {
  const t = editorVideo.currentTime || 0;
  editorTime.textContent = fmtTime(t);
  const active = editorChunks.find(c => t >= c.start && t <= c.end);
  if (active && active.id !== activeCaptionId) {
    activeCaptionId = active.id;
    document.querySelectorAll('.caption-row').forEach(r => r.classList.toggle('active', Number(r.dataset.id) === activeCaptionId));
  }
  updateEditorOverlay();
});
setupVideoAudioSync(editorVideo, editorVolume, editorVolumeValue, editorPlayBtn, 'Play with audio');
function getVideoContentRect() {
  const stage = document.getElementById('editorVideoStage');
  if (!stage) return null;
  const videoRect = editorVideo.getBoundingClientRect();
  const stageRect = stage.getBoundingClientRect();
  const vw = Number(editorVideo.videoWidth) || 0;
  const vh = Number(editorVideo.videoHeight) || 0;
  if (!videoRect.width || !videoRect.height) return null;

  // The <video> element can be wider than the actual portrait/vertical picture
  // because the browser puts black letterbox bars inside it. Captions must be
  // constrained to the real picture rectangle, not the full player rectangle.
  let contentWidth = videoRect.width;
  let contentHeight = videoRect.height;
  let contentLeft = videoRect.left;
  let contentTop = videoRect.top;

  if (vw > 0 && vh > 0) {
    const videoRatio = vw / vh;
    const boxRatio = videoRect.width / videoRect.height;
    if (boxRatio > videoRatio) {
      contentHeight = videoRect.height;
      contentWidth = contentHeight * videoRatio;
      contentLeft = videoRect.left + (videoRect.width - contentWidth) / 2;
    } else if (boxRatio < videoRatio) {
      contentWidth = videoRect.width;
      contentHeight = contentWidth / videoRatio;
      contentTop = videoRect.top + (videoRect.height - contentHeight) / 2;
    }
  }

  return {
    left: contentLeft - stageRect.left,
    top: contentTop - stageRect.top,
    width: contentWidth,
    height: contentHeight,
    stageWidth: stageRect.width,
    stageHeight: stageRect.height,
  };
}

function positionEditorCaption(contentRect, positionPercent) {
  if (!contentRect) return;
  const centerX = contentRect.left + contentRect.width / 2;
  const desiredY = contentRect.top + contentRect.height * (Number(positionPercent) / 100);

  editorCaptionOverlay.style.left = `${centerX}px`;
  editorCaptionOverlay.style.top = `${desiredY}px`;
  editorCaptionOverlay.style.transform = 'translate(-50%, -50%)';
  editorCaptionOverlay.style.transformOrigin = 'center center';
  editorCaptionOverlay.style.textAlign = 'center';
  editorCaptionOverlay.style.width = 'max-content';
  editorCaptionOverlay.style.maxWidth = `${Math.max(120, Math.round(contentRect.width * 0.92))}px`;
  editorCaptionOverlay.style.padding = '0';
  editorCaptionOverlay.style.boxSizing = 'border-box';
  editorCaptionOverlay.style.zoom = '';
}

function clampEditorCaptionToVideo(contentRect) {
  if (!contentRect) return;
  const stage = document.getElementById('editorVideoStage');
  if (!stage) return;

  const centerX = contentRect.left + contentRect.width / 2;
  editorCaptionOverlay.style.left = `${centerX}px`;
  editorCaptionOverlay.style.transformOrigin = 'center center';

  const overlayRect = editorCaptionOverlay.getBoundingClientRect();
  const currentTop = parseFloat(editorCaptionOverlay.style.top) || (contentRect.top + contentRect.height * (Number(positionRange.value || 78) / 100));
  const halfH = (overlayRect.height / 2) || 20;
  const margin = Math.max(5, Math.round(contentRect.height * 0.012));
  const minY = contentRect.top + halfH + margin;
  const maxY = contentRect.top + contentRect.height - halfH - margin;
  const safeY = Math.min(Math.max(currentTop, minY), Math.max(minY, maxY));
  editorCaptionOverlay.style.top = `${safeY}px`;
  editorCaptionOverlay.style.transform = 'translate(-50%, -50%)';
  editorCaptionOverlay.style.zoom = '';
}

function applyEditorTemplateObject(el, template, contentScale, active=false) {
  if (!el) return;
  el.classList.toggle('word-active', !!active);
  el.style.textDecoration = 'none';
  el.style.textDecorationLine = 'none';
  el.style.borderBottom = '0';
}

function templateDisplayWord(text, template) {
  const value = String(text ?? '');
  const mode = template?.text_case || 'sentence';
  if (mode === 'upper') return value.toUpperCase();
  if (mode === 'lower') return value.toLowerCase();
  return value;
}

function updateEditorOverlay() {
  const t = editorVideo.currentTime || 0;
  let c = editorChunks.find(x => t >= Number(x.start) && t <= Number(x.end));
  if (!c && editorVideo.paused && activeCaptionId) {
    c = getChunkById(activeCaptionId);
  }
  if (!c) {
    editorCaptionOverlay.hidden = true;
    currentAnimatedChunkId = null;
    return;
  }

  const template = editorTemplateObject || selectedTemplateObject || templateById(editorTemplateId || selectedTemplate);
  const words = Array.isArray(c.words) && c.words.length
    ? c.words
    : c.text.split(/\s+/).filter(Boolean).map((word, i, arr) => ({
        text: word,
        start: c.start + (c.end-c.start) * i / arr.length,
        end: c.start + (c.end-c.start) * (i+1) / arr.length
      }));
  const activeWord = words.findIndex(w => t >= Number(w.start) && t <= Number(w.end));
  const signature = `${c.id}|${c.text}|${words.length}|${template.id}|${template.text_case}|${template.chunk_words}|${template.max_lines}`;

  const animName = template.animation || 'pop';
  const animClass = animName === 'bounce' ? 'anim-bounce'
                  : animName === 'scale_in' ? 'anim-scale-in'
                  : animName === 'slide' ? 'anim-slide'
                  : animName === 'fade' ? 'anim-fade'
                  : animName === 'glow_pulse' ? 'anim-glow-pulse'
                  : 'anim-pop';

  editorCaptionOverlay.hidden = false;
  editorCaptionOverlay.className = `editor-caption-overlay ${template.css_class || template.cls || ''} ${animClass}`;
  if (template.max_lines === 1 || Number(template.span_scale || 0.65) >= 0.95) {
    editorCaptionOverlay.classList.add('single-tier');
  } else {
    editorCaptionOverlay.classList.remove('single-tier');
  }

  // Animation synchronized to caption chunk
  if (c.id !== currentAnimatedChunkId) {
    currentAnimatedChunkId = c.id;
    editorCaptionOverlay.classList.remove('anim-pop', 'anim-bounce', 'anim-scale-in', 'anim-slide', 'anim-fade', 'anim-glow-pulse');
    void editorCaptionOverlay.offsetWidth;
    editorCaptionOverlay.classList.add(animClass);
  }

  if (signature !== lastOverlaySignature) {
    lastOverlaySignature = signature;
    editorCaptionOverlay.innerHTML = '';

    const lineWordGroups = partitionWordsJS(words, template, c.text);

    let cursor = 0;
    lineWordGroups.forEach((group, lineIdx) => {
      if (!group.length) return;
      const lineDiv = document.createElement('div');
      lineDiv.className = 'caption-line';
      const tagName = (lineWordGroups.length > 1 && lineIdx === 0) ? 'span' : 'strong';
      const wrapper = document.createElement(tagName);
      group.forEach((w, localIndex) => {
        const idx = cursor + localIndex;
        const el = document.createElement('span');
        el.className = `tracked-word${idx === activeWord ? ' word-active' : ''}`;
        el.dataset.wordIndex = String(idx);
        el.textContent = templateDisplayWord(w.text || '', template);
        wrapper.appendChild(el);
        if (localIndex < group.length - 1) wrapper.appendChild(document.createTextNode(' '));
      });
      lineDiv.appendChild(wrapper);
      editorCaptionOverlay.appendChild(lineDiv);
      cursor += group.length;
    });
  }

  // Active state is refreshed without rebuilding the DOM.
  editorCaptionOverlay.querySelectorAll('.tracked-word').forEach((el, i) => {
    el.classList.toggle('word-active', i === activeWord);
  });

  const contentRect = getVideoContentRect();
  if (!contentRect) return;

  // Exact 1:1 proportional sizing synchronized with ASS canvas (720px base)
  const baseCanvasWidth = 720.0;
  const tmplFontSize = Number(template.font_size || 52);
  const userScale = Number(fontSize.value || 54) / 54.0;
  const computedFontSize = contentRect.width * (tmplFontSize / baseCanvasWidth) * userScale;

  editorCaptionOverlay.style.setProperty('--caption-font-size', `${Math.max(12, computedFontSize)}px`);
  editorCaptionOverlay.style.setProperty('--span-scale', template.span_scale || (template.max_lines === 1 ? '1.0' : '0.65'));
  editorCaptionOverlay.style.setProperty('--line-height', String(template.line_height || 0.90));
  editorCaptionOverlay.style.setProperty('--letter-spacing', `${template.letter_spacing || 0}px`);
  editorCaptionOverlay.style.setProperty('--highlight-color', template.highlight_color || '#ffe600');

  positionEditorCaption(contentRect, positionRange.value);
  requestAnimationFrame(() => clampEditorCaptionToVideo(contentRect));

  const row = document.querySelector(`.caption-row[data-id="${c.id}"]`);
  if (row) row.querySelectorAll('.word-chip').forEach((chip, i) => chip.classList.toggle('speaking', i === activeWord));
}

editorVideo.addEventListener('loadedmetadata', () => {
  if (!captionEditor.hidden) updateEditorOverlay();
});
window.addEventListener('resize', () => {
  if (!captionEditor.hidden) updateEditorOverlay();
});

addCaptionBtn.addEventListener('click', () => {
  const last = editorChunks[editorChunks.length-1];
  const start = last ? Number(last.end)+0.02 : Number(editorVideo.currentTime || 0);
  const end = Math.min(start+1.5, (editorVideo.duration || start+1.5));
  const tmpl = editorTemplateObject || selectedTemplateObject || templateById(editorTemplateId || selectedTemplate);
  const wordCount = Math.max(1, Number(tmpl?.chunk_words || 3));
  const sampleWords = ['Type', 'your', 'caption', 'here'].slice(0, wordCount);
  const formattedText = formatCaptionLinesJS(sampleWords, tmpl);
  const duration = Math.max(0.2, end - start);
  const perWord = duration / sampleWords.length;
  const newChunk = {
    id: editorChunks.length+1,
    start,
    end,
    text: formattedText,
    template_id: editorTemplateId || selectedTemplate,
    template: tmpl,
    words: sampleWords.map((w, i) => ({
      text: w,
      start: start + i * perWord,
      end: i === sampleWords.length - 1 ? end : start + (i + 1) * perWord,
    })),
    pattern_words: wordCount,
    pattern_max_chars: Number(tmpl?.max_chars || 28),
    pattern_max_lines: Number(tmpl?.max_lines || 2),
  };
  editorChunks.push(newChunk); renumberChunks(); activeCaptionId = newChunk.id;
  renderCaptionRows();
  const row = document.querySelector(`.caption-row[data-id="${newChunk.id}"]`);
  if (row) { row.scrollIntoView({behavior:'smooth',block:'center'}); row.querySelector('.caption-text').focus(); }
  editorVideo.currentTime = start; editorVideo.pause(); updateEditorOverlay();
});
resetCaptionsBtn.addEventListener('click', () => {
  editorChunks = cloneChunks(originalEditorChunks);
  activeCaptionId = null;
  renderCaptionRows(); updateEditorOverlay();
});
backToSettingsBtn.addEventListener('click', () => {
  if (editorVideo) {
    try { editorVideo.pause(); } catch (_) {}
    editorVideo.removeAttribute('src');
    editorVideo.load();
  }
  captionEditor.hidden = true; form.hidden = false; progressWrap.hidden = true;
  if (videoInput.files && videoInput.files[0]) {
    sourcePreview.src = makeVideoBlobUrl(videoInput.files[0]);
    sourcePreview.defaultMuted = false;
    sourcePreview.muted = false;
    const vol = Number(sourceVolume?.value || 100) / 100;
    sourcePreview.volume = Math.max(0.05, isNaN(vol) ? 1.0 : vol);
    sourcePreview.load();
    sourcePreviewWrap.hidden = false;
  }
  submitBtn.disabled = !videoInput.files[0];
  window.scrollTo({top: form.offsetTop - 20, behavior:'smooth'});
});
renderEditedBtn.addEventListener('click', async () => {
  if (!editorSessionId) return;
  // Sync any currently focused/edited row before exporting.
  const focusedRow = document.activeElement?.closest?.('.caption-row');
  if (focusedRow) updateChunkFromRow(focusedRow);
  renderEditedBtn.disabled = true; renderSpinner.hidden = false; renderEditedText.textContent = 'Rendering…';
  try {
    const response = await fetch('/api/editor/render', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({session_id:editorSessionId,chunks:editorChunks,template:editorTemplateObject || selectedTemplateObject || templateById(editorTemplateId),font_size:Number(fontSize.value),position_percent:Number(positionRange.value),audio_volume:Number(exportVolume.value)})
    });
    if (!response.ok) {
      const err = await response.json().catch(()=>({}));
      throw new Error(err.detail || 'Could not render the edited video.');
    }
    const blob = await response.blob();
    if (resultUrl) URL.revokeObjectURL(resultUrl);
    resultUrl = URL.createObjectURL(blob);
    if (editorVideo) {
      try { editorVideo.pause(); } catch (_) {}
      editorVideo.removeAttribute('src');
      editorVideo.load();
    }
    resultVideo.src = resultUrl;
    resultVideo.defaultMuted = false;
    resultVideo.muted = false;
    const resVol = Number(resultVolume?.value || 100) / 100;
    resultVideo.volume = Math.max(0.05, isNaN(resVol) ? 1.0 : resVol);
    resultVideo.load();
    resultAudioBtn.textContent = 'Play with audio';
    const originalName = (videoInput.files[0]?.name || 'video').replace(/\.[^/.]+$/, '');
    downloadBtn.href = resultUrl; downloadBtn.download = `captioned-${originalName}-edited.mp4`;
    detectedLanguage.textContent = `Detected speech: ${editorStatus.textContent} · Captions checked and corrected`;
    captionEditor.hidden = true; result.hidden = false;
    window.scrollTo({top:result.offsetTop-20,behavior:'smooth'});
  } catch (err) {
    showError(err.message || 'Could not render the edited video.');
  } finally {
    renderEditedBtn.disabled = false; renderSpinner.hidden = true; renderEditedText.textContent = 'Render corrected video';
  }
});

const editorFontSizeRange = document.getElementById('editorFontSizeRange');
const editorFontSizeVal = document.getElementById('editorFontSizeVal');
const editorPosRange = document.getElementById('editorPosRange');
const editorPosVal = document.getElementById('editorPosVal');
const editorSpeed = document.getElementById('editorSpeed');

if (editorFontSizeRange) {
  editorFontSizeRange.addEventListener('input', () => {
    fontSize.value = editorFontSizeRange.value;
    fontSizeValue.textContent = `${editorFontSizeRange.value}px`;
    if (editorFontSizeVal) editorFontSizeVal.textContent = `${editorFontSizeRange.value}px`;
    if (!captionEditor.hidden) updateEditorOverlay();
  });
}

if (editorPosRange) {
  editorPosRange.addEventListener('input', () => {
    positionRange.value = editorPosRange.value;
    positionValue.textContent = `${editorPosRange.value}%`;
    if (editorPosVal) editorPosVal.textContent = `${editorPosRange.value}%`;
    if (!captionEditor.hidden) updateEditorOverlay();
  });
}

if (editorSpeed) {
  editorSpeed.addEventListener('change', () => {
    editorVideo.playbackRate = Number(editorSpeed.value) || 1.0;
  });
}

positionRange.addEventListener('input', () => {
  if (editorPosRange) editorPosRange.value = positionRange.value;
  if (editorPosVal) editorPosVal.textContent = `${positionRange.value}%`;
  if (!captionEditor.hidden) updateEditorOverlay();
});

fontSize.addEventListener('input', () => {
  if (editorFontSizeRange) editorFontSizeRange.value = fontSize.value;
  if (editorFontSizeVal) editorFontSizeVal.textContent = `${fontSize.value}px`;
  if (!captionEditor.hidden) updateEditorOverlay();
});

window.addEventListener('keydown', e => {
  if (captionEditor.hidden) return;
  const tag = document.activeElement?.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
  if (e.code === 'Space') {
    e.preventDefault();
    editorPlayBtn.click();
  } else if (e.code === 'KeyJ') {
    e.preventDefault();
    editorVideo.currentTime = Math.max(0, editorVideo.currentTime - 2);
  } else if (e.code === 'KeyL') {
    e.preventDefault();
    editorVideo.currentTime = Math.min(editorVideo.duration || 9999, editorVideo.currentTime + 2);
  }
});

exportVolume.addEventListener('input', () => {
  exportVolumeValue.textContent = `${exportVolume.value}%`;
});

function resetProcessingState() {
  spinner.hidden = true;
  submitText.textContent = 'Generate captions';
  submitBtn.disabled = !videoInput.files[0];
  progressWrap.hidden = true;
}
function showError(message) { errorBox.textContent = message; errorBox.hidden = false; }
function hideError() { errorBox.hidden = true; errorBox.textContent = ''; }

startOverBtn.addEventListener('click', () => {
  captionEditor.hidden = true; editorSessionId = null; editorChunks = []; originalEditorChunks = []; activeCaptionId = null; lastOverlaySignature = ""; currentAnimatedChunkId = null;
  editorVideo.removeAttribute('src'); editorVideo.load();
  if (resultUrl) { URL.revokeObjectURL(resultUrl); resultUrl = null; }
  resultVideo.removeAttribute('src');
  resultVideo.load();
  if (sourceUrl) { URL.revokeObjectURL(sourceUrl); sourceUrl = null; }
  sourcePreview.removeAttribute('src');
  sourcePreview.load();
  sourcePreviewWrap.hidden = true;
  result.hidden = true;
  form.hidden = false;
  form.reset();
  filePill.hidden = true;
  submitBtn.disabled = true;
  selectedTemplate = 'bold_white';
  selectedTemplateObject = templateById('bold_white');
  editorTemplateId = 'bold_white';
  editorTemplateObject = selectedTemplateObject;
  document.querySelector('input[name="template"][value="bold_white"]').checked = true;
  document.querySelectorAll('.template-card').forEach(card => card.classList.remove('selected'));
  document.querySelector('input[name="template"][value="bold_white"]').closest('.template-card').classList.add('selected');
  fontSize.value = 54;
  fontSizeValue.textContent = '54';
  positionRange.value = 78;
  positionValue.textContent = '78%';
  positionPreset.value = 'bottom';
  sourceVolume.value = 100;
  sourceVolumeValue.textContent = '100%';
  exportVolume.value = 100;
  exportVolumeValue.textContent = '100%';
  resultVolume.value = 100;
  resultVolumeValue.textContent = '100%';
  applyPreviewTemplate();
  applyPreviewPosition();
  hideError();
});

selectedTemplateObject = templateById(selectedTemplate);
renderTemplates();
applyPreviewTemplate();
applyPreviewPosition();
loadTemplateContract();
