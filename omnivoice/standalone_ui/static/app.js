import { browserLanguage, initializeI18n, t } from './i18n.js'
import { AudioEditor } from './audio-editor.js'

await initializeI18n()

const $ = (selector, root = document) => root.querySelector(selector)
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)]

const state = {
  activeTab: 'generate',
  headerCollapsed: false,
  backendReady: false,
  streamAbort: null,
  streamPlayback: null,
  profiles: [],
  gpuHistory: new Map(),
  gpuStats: [],
  gpuWindowMs: 60 * 1000,
  gpuTimer: null,
  gpuRefreshActive: false,
  gpuHovering: false,
  headerAnimation: null,
  inputType: 'text',
  normalizationAbort: null,
}

const UI_SESSION_KEY = 'omnivoicetts-ui-state-v1'
const GPU_SESSION_KEY = 'omnivoicetts-gpu-history-v1'
const GPU_HISTORY_RETENTION_MS = 10 * 60 * 1000
const GPU_POLL_INTERVAL_MS = 1000
const SAMPLE_TEXTS = [
  'Hello from OmniVoice. This local voice system supports more than six hundred languages.',
  'The quickest way to understand a voice is to hear it explain something clearly and naturally.',
  'That timing was almost perfect. [laughter] Let us try the line one more time.',
  'A consistent saved voice can speak new text without uploading the same reference for every request.',
]
const SSML_SAMPLES = [
  `<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
  Welcome to <sub alias="Hangry Labs">HangryLabs</sub>.
  <break time="300ms"/>
  <prosody rate="slow" pitch="+2st">This sentence uses standard SSML controls.</prosody>
</speak>`,
  `<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
  Spell <say-as interpret-as="characters">SSML</say-as>, then pause.
  <break strength="medium"/>
  Continue at <prosody rate="120%">a slightly faster rate</prosody>.
</speak>`,
]
const SSML_H_SAMPLES = [
  `<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:h="https://hangrylabs.app/ns/ssml-h/1.0" xml:lang="en-US">
  <metadata>
    <h:extensions version="1.0">
      <h:voice-definition name="Bob" gender="male" age="elderly" accent="american" scope="request" seed="4242">
        <h:sample xml:lang="en-US">My name is Bob. I am ready for this conversation.</h:sample>
      </h:voice-definition>
      <h:voice-definition name="Elisabeth" gender="female" age="elderly" accent="american" scope="request" seed="8241"/>
    </h:extensions>
  </metadata>
  <voice name="Bob">Are we ready?</voice>
  <break time="300ms"/>
  <voice name="Elisabeth"><prosody rate="slow">Yes, all preparations are complete.</prosody></voice>
</speak>`,
]
const DEFAULT_CONTROLS = {
  voice_mode: 'random', language: '', voice_profile: '', device: 'auto', output_format: 'mp3',
  speed: 1, pitch_semitones: 0, tempo: 1, volume: 1, normalize: false, normalize_text: false, num_step: 32,
  guidance_scale: 2, pad_duration: 0.1, fade_duration: 0.1, seed: 42,
  randomize_seed: true, denoise: true, preprocess_prompt: true, postprocess_output: true,
  audio_chunk_duration: 15, audio_chunk_threshold: 30,
}
const GPU_METRICS = [
  { key: 'utilization', label: t('gpu.metric.gpu'), color: '#ff7a1a' },
  { key: 'memory_utilization', label: t('gpu.metric.memoryActivity'), color: '#c586c0' },
  { key: 'memory_used', label: t('gpu.metric.vram'), color: '#72a7ff' },
  { key: 'temperature', label: t('gpu.metric.temperature'), color: '#ef6b73' },
  { key: 'power', label: t('gpu.metric.power'), color: '#f2c94c' },
  { key: 'fan_speed', label: t('gpu.metric.fan'), color: '#55c58a' },
  { key: 'graphics_clock', label: t('gpu.metric.graphicsClock'), color: '#9cdcfe' },
  { key: 'memory_clock', label: t('gpu.metric.memoryClock'), color: '#ce9178' },
]
const AUDIO_EDITOR_LABELS = {
  noAudio: t('audio.noAudio', {}, 'No audio selected'),
  download: t('output.download', {}, 'Download audio'),
  share: t('audio.share', {}, 'Share audio'),
  remove: t('audio.remove', {}, 'Remove audio'),
  mute: t('audio.mute', {}, 'Mute or unmute'),
  volume: t('audio.volume', {}, 'Volume'),
  playbackSpeed: t('audio.playbackSpeed', {}, 'Playback speed'),
  backward: t('audio.backward', {}, 'Seek backward 5 seconds'),
  play: t('audio.play', {}, 'Play'),
  pause: t('audio.pause', {}, 'Pause'),
  forward: t('audio.forward', {}, 'Seek forward 5 seconds'),
  restart: t('audio.restart', {}, 'Return to start'),
  trim: t('audio.trim', {}, 'Select and trim audio'),
  cancel: t('common.cancel', {}, 'Cancel'),
  applySelection: t('audio.applySelection', {}, 'Apply selection'),
}

const generateOutput = new AudioEditor($('#generate-output'), {
  label: t('output.generated', {}, 'Generated audio'),
  emptyTitle: t('output.emptyTitle', {}, 'Audio output'),
  emptyDescription: t('output.emptyReady', {}, 'Ready for synthesis'),
  labels: AUDIO_EDITOR_LABELS,
})
const streamOutput = new AudioEditor($('#stream-output'), {
  label: t('output.streamed', {}, 'Streamed audio'),
  emptyTitle: t('output.emptyTitle', {}, 'Audio output'),
  emptyDescription: t('output.emptyStream', {}, 'Ready for streaming'),
  labels: AUDIO_EDITOR_LABELS,
})
const profileAudio = new AudioEditor($('#profile-audio-preview'), {
  label: t('voices.referencePreview', {}, 'Reference preview'),
  emptyTitle: t('voices.noReference', {}, 'No reference selected'),
  emptyDescription: t('voices.referenceReady', {}, 'Choose a sample to inspect it here'),
  labels: AUDIO_EDITOR_LABELS,
  onChange: (file) => {
    $('#profile-audio-drop').classList.toggle('has-file', Boolean(file))
  },
})

for (const editor of [generateOutput, streamOutput, profileAudio]) {
  editor.container.addEventListener('audio-error', (event) => showToast(errorMessage(event.detail)))
}

function errorMessage(error) {
  return error instanceof Error ? error.message : String(error)
}

async function responseError(response) {
  const text = await response.text()
  try {
    const payload = JSON.parse(text)
    return payload.error?.message || payload.detail || text
  } catch {
    return text || `HTTP ${response.status}`
  }
}

async function fetchJson(path, options) {
  const response = await fetch(path, options)
  if (!response.ok) throw new Error(await responseError(response))
  return response.json()
}

function setStatus(message, tone = 'neutral') {
  const status = $('#global-status')
  status.textContent = message
  status.dataset.tone = tone
}

function showToast(message, tone = 'error') {
  const toast = $('#toast')
  toast.textContent = message
  toast.dataset.tone = tone
  toast.hidden = false
  clearTimeout(showToast.timer)
  showToast.timer = setTimeout(() => { toast.hidden = true }, 5000)
}

function readSessionJson(key) {
  try { return JSON.parse(sessionStorage.getItem(key) || 'null') } catch { return null }
}

function persistUiSession() {
  try {
    sessionStorage.setItem(UI_SESSION_KEY, JSON.stringify({
      activeTab: state.activeTab,
      headerCollapsed: state.headerCollapsed,
      gpuWindowMs: state.gpuWindowMs,
      inputType: state.inputType,
    }))
  } catch {}
}

function persistGpuSession() {
  try {
    sessionStorage.setItem(GPU_SESSION_KEY, JSON.stringify({
      savedAt: Date.now(), stats: state.gpuStats, history: Object.fromEntries(state.gpuHistory),
    }))
  } catch {}
}

function restoreSessionState() {
  const ui = readSessionJson(UI_SESSION_KEY)
  if (['generate', 'stream', 'voices', 'api', 'system'].includes(ui?.activeTab)) state.activeTab = ui.activeTab
  if (typeof ui?.headerCollapsed === 'boolean') state.headerCollapsed = ui.headerCollapsed
  if ([60 * 1000, 10 * 60 * 1000].includes(ui?.gpuWindowMs)) state.gpuWindowMs = ui.gpuWindowMs
  if (['text', 'ssml', 'ssml-h'].includes(ui?.inputType)) state.inputType = ui.inputType

  const cached = readSessionJson(GPU_SESSION_KEY)
  const cutoff = Date.now() - GPU_HISTORY_RETENTION_MS
  if (!cached || !Number.isFinite(cached.savedAt) || cached.savedAt < cutoff) return
  if (Array.isArray(cached.stats)) state.gpuStats = cached.stats
  Object.entries(cached.history || {}).forEach(([index, samples]) => {
    const recent = Array.isArray(samples)
      ? samples.filter((sample) => Number.isFinite(sample?.timestamp) && sample.timestamp >= cutoff)
      : []
    if (recent.length) state.gpuHistory.set(Number(index), recent)
  })
}

function setHeroCollapsed(collapsed, persist = true, animate = true) {
  const hero = $('#brand-hero')
  const toggle = $('#hero-toggle')
  state.headerAnimation?.cancel()
  const startHeight = hero.getBoundingClientRect().height
  state.headerCollapsed = collapsed
  const action = collapsed ? t('hero.expand') : t('hero.collapse')
  document.documentElement.dataset.headerCollapsed = String(collapsed)
  hero.dataset.collapsed = String(collapsed)
  toggle.setAttribute('aria-expanded', String(!collapsed))
  toggle.setAttribute('aria-label', action)
  toggle.title = action
  toggle.querySelector('i').className = collapsed ? 'icon-chevron-down' : 'icon-chevron-up'
  const endHeight = hero.getBoundingClientRect().height
  if (animate && !matchMedia('(prefers-reduced-motion: reduce)').matches && Math.abs(startHeight - endHeight) > 1) {
    hero.classList.add('is-rolling')
    const animation = hero.animate(
      [{ height: `${startHeight}px` }, { height: `${endHeight}px` }],
      { duration: 320, easing: 'cubic-bezier(0.22, 1, 0.36, 1)', fill: 'both' },
    )
    state.headerAnimation = animation
    animation.finished.catch(() => {}).finally(() => {
      if (state.headerAnimation !== animation) return
      hero.classList.remove('is-rolling')
      state.headerAnimation = null
      animation.cancel()
    })
  }
  if (persist) persistUiSession()
}

function activateTab(name) {
  state.activeTab = name
  $('.workspace').dataset.view = name
  $$('.tab-button').forEach((button) => {
    const active = button.dataset.tab === name
    button.classList.toggle('active', active)
    button.setAttribute('aria-selected', String(active))
  })
  $$('.tab-panel').forEach((panel) => { panel.hidden = panel.dataset.panel !== name })
  if (name === 'system') {
    refreshSystem().catch((error) => showToast(errorMessage(error)))
    startGpuMonitor()
  } else {
    stopGpuMonitor()
  }
  if (name === 'voices') refreshProfiles().catch((error) => showToast(errorMessage(error)))
  if (name === 'api') refreshApiStatus().catch((error) => showToast(errorMessage(error)))
  persistUiSession()
}

$('#hero-toggle').addEventListener('click', () => setHeroCollapsed(!state.headerCollapsed))
$$('.tab-button').forEach((button) => button.addEventListener('click', () => activateTab(button.dataset.tab)))

function bindRangePairs() {
  $$('[data-value-input]').forEach((slider) => {
    const number = $(`#${slider.dataset.valueInput}`)
    slider.addEventListener('input', () => { number.value = slider.value })
    number.addEventListener('input', () => { slider.value = number.value })
  })
}

function updateTextMetrics() {
  $('#text-metrics').textContent = t('composer.characters', { count: $('#text-input').value.length })
}

function hideNormalizationPreview() {
  state.normalizationAbort?.abort()
  state.normalizationAbort = null
  $('#normalization-preview').hidden = true
}

async function refreshNormalizationPreview() {
  clearTimeout(refreshNormalizationPreview.timer)
  state.normalizationAbort?.abort()
  const enabled = $('#normalize-text').checked && state.inputType === 'text'
  const text = $('#text-input').value.trim()
  if (!enabled || !text) {
    hideNormalizationPreview()
    return
  }

  const controller = new AbortController()
  state.normalizationAbort = controller
  try {
    const payload = await fetchJson('/tts/text/normalize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language: $('#language').value || null }),
      signal: controller.signal,
    })
    if (state.normalizationAbort !== controller) return
    const warnings = [...(payload.warnings || [])]
    if (!payload.supported && !warnings.length) warnings.push(t('composer.normalizationUnsupported'))
    $('#normalization-output').textContent = payload.normalized
    $('#normalization-change-count').textContent = t('composer.normalizationChanges', { count: payload.changes?.length || 0 })
    $('#normalization-warnings').textContent = warnings.join(' ')
    $('#normalization-warnings').hidden = !warnings.length
    $('#normalization-preview').hidden = false
  } catch (error) {
    if (error.name !== 'AbortError') hideNormalizationPreview()
  } finally {
    if (state.normalizationAbort === controller) state.normalizationAbort = null
  }
}

function scheduleNormalizationPreview() {
  clearTimeout(refreshNormalizationPreview.timer)
  refreshNormalizationPreview.timer = setTimeout(refreshNormalizationPreview, 300)
}

function samplesForInputType(inputType = state.inputType) {
  if (inputType === 'ssml') return SSML_SAMPLES
  if (inputType === 'ssml-h') return SSML_H_SAMPLES
  return SAMPLE_TEXTS
}

function setInputType(inputType, { replaceKnownSample = true, persist = true } = {}) {
  if (!['text', 'ssml', 'ssml-h'].includes(inputType)) return
  const editor = $('#text-input')
  const previousSamples = samplesForInputType(state.inputType)
  const shouldReplace = replaceKnownSample && (!editor.value.trim()
    || previousSamples.includes(editor.value)
    || editor.value === t('composer.defaultText'))
  state.inputType = inputType
  editor.dataset.inputType = inputType
  editor.spellcheck = inputType === 'text'
  $$('[data-input-type]').forEach((button) => {
    const active = button.dataset.inputType === inputType
    button.classList.toggle('active', active)
    button.setAttribute('aria-pressed', String(active))
  })
  $('#expression-guide-button').hidden = inputType !== 'text'
  $('#normalize-text').disabled = inputType !== 'text'
  if (shouldReplace) editor.value = samplesForInputType(inputType)[0]
  updateTextMetrics()
  scheduleNormalizationPreview()
  if (persist) persistUiSession()
}

function populateSelect(select, options, selected = '') {
  select.replaceChildren(...options.map(({ value, label }) => {
    const option = document.createElement('option')
    option.value = value
    option.textContent = label
    option.selected = value === selected
    return option
  }))
}

function nativeLanguageLabel(id, fallback) {
  if (!id || !('DisplayNames' in Intl)) return fallback
  try {
    const name = new Intl.DisplayNames([id], { type: 'language' }).of(id)
    if (!name || name.toLocaleLowerCase() === id.toLocaleLowerCase()) return fallback
    const [first, ...rest] = [...name]
    return `${first.toLocaleUpperCase(id)}${rest.join('')}`
  } catch {
    return fallback
  }
}

function setControlValue(control, value) {
  const requested = String(value)
  if (control instanceof HTMLSelectElement) {
    const option = [...control.options].find((item) => item.value === requested)
      || [...control.options].find((item) => item.value.toLowerCase() === requested.toLowerCase())
    control.value = option?.value ?? requested
    return
  }
  control.value = requested
}

function updateVoiceMode() {
  const mode = $('#voice-mode').value
  $('#design-panel').hidden = mode !== 'design'
  $('#clone-panel').hidden = mode !== 'clone'
  $('#profile-field').hidden = mode !== 'profile'
}

function controlValues() {
  return {
    voice_mode: $('#voice-mode').value,
    language: $('#language').value,
    voice_profile: $('#voice-profile').value,
    device: $('#device').value,
    output_format: $('#output-format').value,
    speed: Number($('#speed').value),
    pitch_semitones: Number($('#pitch').value),
    tempo: Number($('#tempo').value),
    volume: Number($('#volume').value),
    normalize: $('#normalize').checked,
    normalize_text: $('#normalize-text').checked,
    num_step: Number($('#num-step').value),
    guidance_scale: Number($('#guidance-scale').value),
    pad_duration: Number($('#pad-duration').value),
    fade_duration: Number($('#fade-duration').value),
    seed: Number($('#seed').value),
    randomize_seed: $('#randomize-seed').checked,
    denoise: $('#denoise').checked,
    preprocess_prompt: $('#preprocess-prompt').checked,
    postprocess_output: $('#postprocess-output').checked,
    audio_chunk_duration: Number($('#audio-chunk-duration').value),
    audio_chunk_threshold: Number($('#audio-chunk-threshold').value),
  }
}

function applyControlValues(values = {}) {
  const settings = { ...DEFAULT_CONTROLS, ...values }
  const direct = {
    '#voice-mode': settings.voice_mode, '#language': settings.language, '#voice-profile': settings.voice_profile,
    '#device': settings.device, '#output-format': settings.output_format, '#speed': settings.speed,
    '#speed-slider': settings.speed, '#pitch': settings.pitch_semitones, '#pitch-slider': settings.pitch_semitones,
    '#tempo': settings.tempo, '#tempo-slider': settings.tempo, '#volume': settings.volume,
    '#volume-slider': settings.volume, '#num-step': settings.num_step, '#guidance-scale': settings.guidance_scale,
    '#pad-duration': settings.pad_duration, '#fade-duration': settings.fade_duration, '#seed': settings.seed,
    '#audio-chunk-duration': settings.audio_chunk_duration, '#audio-chunk-threshold': settings.audio_chunk_threshold,
  }
  Object.entries(direct).forEach(([selector, value]) => {
    const input = $(selector)
    if (input && value !== undefined && value !== null) setControlValue(input, value)
  })
  $('#normalize').checked = settings.normalize === true
  $('#normalize-text').checked = settings.normalize_text === true
  $('#randomize-seed').checked = settings.randomize_seed === true
  $('#denoise').checked = settings.denoise !== false
  $('#preprocess-prompt').checked = settings.preprocess_prompt !== false
  $('#postprocess-output').checked = settings.postprocess_output !== false
  updateVoiceMode()
  scheduleNormalizationPreview()
}

function voiceDesignInstruction() {
  return $$('[data-design]').map((select) => select.value).filter(Boolean).join(', ') || null
}

async function uploadAudio(file) {
  const form = new FormData()
  form.append('audio', file)
  return fetchJson('/ui/reference-audio', { method: 'POST', body: form })
}

async function releaseUpload(token) {
  if (!token) return
  await fetch(`/ui/reference-audio/${encodeURIComponent(token)}`, { method: 'DELETE' }).catch(() => {})
}

async function requestPayload(forceFormat = null) {
  const text = $('#text-input').value.trim()
  if (!text) throw new Error(t('errors.textRequired'))
  const controls = controlValues()
  const payload = {
    text,
    input_type: state.inputType,
    language: controls.language || null,
    device: controls.device,
    output_format: forceFormat || controls.output_format,
    speed: controls.speed,
    pitch_semitones: controls.pitch_semitones,
    tempo: controls.tempo,
    volume: controls.volume,
    normalize: controls.normalize,
    normalize_text: controls.normalize_text && state.inputType === 'text',
    num_step: controls.num_step,
    guidance_scale: controls.guidance_scale,
    pad_duration: controls.pad_duration,
    fade_duration: controls.fade_duration,
    seed: controls.seed,
    randomize_seed: controls.randomize_seed,
    denoise: controls.denoise,
    preprocess_prompt: controls.preprocess_prompt,
    postprocess_output: controls.postprocess_output,
    audio_chunk_duration: controls.audio_chunk_duration,
    audio_chunk_threshold: controls.audio_chunk_threshold,
  }
  let upload = null
  if (controls.voice_mode === 'design') payload.instruct = voiceDesignInstruction()
  if (controls.voice_mode === 'profile') {
    if (!controls.voice_profile) throw new Error(t('errors.profileRequired'))
    payload.voice_profile = controls.voice_profile
  }
  if (controls.voice_mode === 'clone') {
    const file = $('#reference-audio').files[0]
    if (!file) throw new Error(t('errors.referenceRequired'))
    upload = await uploadAudio(file)
    payload.ref_audio = upload.path
    payload.ref_text = $('#reference-text').value.trim() || null
  }
  return { payload, uploadToken: upload?.token || null }
}

async function loadAudioOutput(editor, blob, filename, { autoplay = true, resumeAt = 0 } = {}) {
  await editor.load(blob, filename)
  if (autoplay) editor.playFrom(resumeAt).catch(() => {})
}

$('#generate-button').addEventListener('click', async (event) => {
  const button = event.currentTarget
  button.disabled = true
  let uploadToken = null
  const started = performance.now()
  try {
    setStatus(t('status.generating'))
    const request = await requestPayload()
    uploadToken = request.uploadToken
    const response = await fetch('/tts/generate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request.payload),
    })
    if (!response.ok) throw new Error(await responseError(response))
    const blob = await response.blob()
    const extension = request.payload.output_format === 'ogg' ? 'ogg' : request.payload.output_format
    await loadAudioOutput(generateOutput, blob, `omnivoicetts.${extension}`)
    const seed = response.headers.get('X-OmniVoiceTTS-Seed')
    setStatus(`${t('status.complete')} · ${((performance.now() - started) / 1000).toFixed(2)}s${seed ? ` · seed ${seed}` : ''}`, 'success')
  } catch (error) {
    setStatus(t('status.failed'), 'error')
    showToast(errorMessage(error))
  } finally {
    await releaseUpload(uploadToken)
    button.disabled = false
  }
})

class IncrementalAudioPlayback {
  static async create() {
    if (!window.MediaSource || !MediaSource.isTypeSupported('audio/mpeg')) return null
    const mediaSource = new MediaSource()
    const objectUrl = URL.createObjectURL(mediaSource)
    const audio = new Audio(objectUrl)
    await new Promise((resolve, reject) => {
      mediaSource.addEventListener('sourceopen', resolve, { once: true })
      mediaSource.addEventListener('error', reject, { once: true })
    })
    try { return new IncrementalAudioPlayback(mediaSource, audio, objectUrl) } catch {
      URL.revokeObjectURL(objectUrl)
      return null
    }
  }

  constructor(mediaSource, audio, objectUrl) {
    this.mediaSource = mediaSource
    this.audio = audio
    this.objectUrl = objectUrl
    this.sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg')
    this.queue = Promise.resolve()
    this.started = false
  }

  append(chunk) {
    const bytes = chunk.buffer.slice(chunk.byteOffset, chunk.byteOffset + chunk.byteLength)
    this.queue = this.queue.then(() => new Promise((resolve, reject) => {
      const done = () => { this.sourceBuffer.removeEventListener('error', failed); resolve() }
      const failed = () => { this.sourceBuffer.removeEventListener('updateend', done); reject(new Error('Browser could not buffer streamed MP3 audio.')) }
      this.sourceBuffer.addEventListener('updateend', done, { once: true })
      this.sourceBuffer.addEventListener('error', failed, { once: true })
      this.sourceBuffer.appendBuffer(bytes)
    })).then(() => {
      if (!this.started) { this.started = true; this.audio.play().catch(() => {}) }
    })
    return this.queue
  }

  async finish() {
    await this.queue
    if (this.mediaSource.readyState === 'open') this.mediaSource.endOfStream()
  }

  currentTime() { return this.audio.currentTime || 0 }
  stop() {
    this.audio.pause()
    if (this.mediaSource.readyState === 'open') { try { this.mediaSource.endOfStream() } catch {} }
    URL.revokeObjectURL(this.objectUrl)
  }
}

function setStreaming(active) {
  $('#stream-start').disabled = active
  $('#stream-stop').disabled = !active
  $('#stream-progress').hidden = !active
}

$('#stream-start').addEventListener('click', async () => {
  const controller = new AbortController()
  const chunks = []
  let uploadToken = null
  let playback = null
  state.streamAbort = controller
  setStreaming(true)
  try {
    setStatus(t('status.streaming'))
    const request = await requestPayload('mp3')
    uploadToken = request.uploadToken
    playback = await IncrementalAudioPlayback.create()
    state.streamPlayback = playback
    const response = await fetch('/tts/stream', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request.payload), signal: controller.signal,
    })
    if (!response.ok) throw new Error(await responseError(response))
    if (!response.body) throw new Error('Streaming response body is unavailable in this browser.')
    const reader = response.body.getReader()
    let totalBytes = 0
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      chunks.push(value)
      totalBytes += value.byteLength
      if (playback) playback.append(value).catch((error) => showToast(errorMessage(error)))
      setStatus(`${t('status.streaming')} · ${(totalBytes / 1024).toFixed(0)} KiB`)
    }
    let resumeAt = 0
    if (playback) {
      await playback.finish()
      resumeAt = playback.currentTime()
      playback.stop()
      playback = null
      state.streamPlayback = null
    }
    await loadAudioOutput(streamOutput, new Blob(chunks, { type: 'audio/mpeg' }), 'omnivoicetts-stream.mp3', {
      autoplay: true,
      resumeAt,
    })
    setStatus(t('status.complete'), 'success')
  } catch (error) {
    if (error.name === 'AbortError') {
      if (chunks.length) await loadAudioOutput(streamOutput, new Blob(chunks, { type: 'audio/mpeg' }), 'omnivoicetts-stream-partial.mp3', { autoplay: false })
      setStatus(t('common.stop'), 'success')
    } else {
      setStatus(t('status.failed'), 'error')
      showToast(errorMessage(error))
    }
  } finally {
    playback?.stop()
    await releaseUpload(uploadToken)
    state.streamAbort = null
    state.streamPlayback = null
    setStreaming(false)
  }
})

$('#stream-stop').addEventListener('click', () => {
  state.streamAbort?.abort()
  state.streamPlayback?.stop()
})

function normalizedProfileName(value) {
  return value.trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^[-_]+|[-_]+$/g, '').slice(0, 48)
}

function updateProfileNamePreview() {
  const normalized = normalizedProfileName($('#profile-name').value)
  const preview = $('#profile-name-preview')
  const note = $('#profile-save-note')
  const noteCopy = $('span', note)
  if (!normalized) {
    preview.textContent = t('voices.nameHint', {}, 'Use letters, numbers, hyphens, or underscores.')
    note.dataset.tone = 'neutral'
    noteCopy.textContent = t('voices.persisted', {}, 'The voice and its audio are stored in the persistent product volume.')
    return
  }
  preview.textContent = t('voices.savedAs', { name: normalized }, `Saved as ${normalized}`)
  const exists = state.profiles.some((profile) => profile.id === normalized)
  note.dataset.tone = exists ? 'warning' : 'neutral'
  noteCopy.textContent = exists
    ? t('voices.overwrite', { name: normalized }, `Saving will replace the existing ${normalized} profile.`)
    : t('voices.persisted', {}, 'The voice and its audio are stored in the persistent product volume.')
}

function useProfile(profile) {
  $('#voice-mode').value = 'profile'
  $('#voice-profile').value = profile.id
  if (profile.language) setControlValue($('#language'), profile.language)
  if (profile.seed != null) $('#seed').value = profile.seed
  $('#randomize-seed').checked = profile.randomize_seed
  updateVoiceMode()
  scheduleNormalizationPreview()
  activateTab('generate')
  setStatus(t('voices.selected', { name: profile.id }, `Voice ${profile.id} selected.`), 'success')
}

let profilePendingDelete = null

function openDeleteProfileDialog(profile) {
  profilePendingDelete = profile
  $('#delete-profile-name').textContent = profile.id
  $('#delete-profile-dialog').showModal()
}

function renderProfileList() {
  const list = $('#profile-list')
  const query = $('#profile-filter').value.trim().toLowerCase()
  const profiles = state.profiles.filter((profile) => profile.id.toLowerCase().includes(query))
  if (!state.profiles.length) {
    const empty = document.createElement('div')
    empty.className = 'empty-profile-list'
    empty.textContent = t('voices.none')
    list.replaceChildren(empty)
    return
  }
  if (!profiles.length) {
    const empty = document.createElement('div')
    empty.className = 'empty-profile-list'
    empty.textContent = t('voices.noMatches', {}, 'No saved voices match this search.')
    list.replaceChildren(empty)
    return
  }
  list.replaceChildren(...profiles.map((profile) => {
    const card = document.createElement('article')
    card.className = 'profile-card'
    const copy = document.createElement('div')
    const title = document.createElement('strong')
    title.textContent = profile.id
    const details = document.createElement('div')
    details.className = 'profile-metadata'
    const badges = [
      profile.language || t('voices.requestLanguage', {}, 'Request language'),
      profile.randomize_seed ? t('voices.randomSeedShort', {}, 'Random seed') : t('voices.fixedSeed', { seed: profile.seed ?? 12345 }, `Seed ${profile.seed ?? 12345}`),
      profile.has_transcript ? t('voices.transcriptSaved', {}, 'Transcript saved') : t('voices.asrRequired', {}, 'ASR on demand'),
    ]
    badges.forEach((label, index) => {
      const badge = document.createElement('span')
      badge.className = index === 2 && !profile.has_transcript ? 'profile-badge warning' : 'profile-badge'
      badge.textContent = label
      details.append(badge)
    })
    copy.append(title, details)
    const actions = document.createElement('div')
    actions.className = 'profile-actions'
    const use = document.createElement('button')
    use.type = 'button'
    use.className = 'secondary-button profile-use'
    use.innerHTML = `<i class="icon-audio-lines"></i><span>${t('voices.use', {}, 'Use')}</span>`
    use.addEventListener('click', () => useProfile(profile))
    const remove = document.createElement('button')
    remove.type = 'button'
    remove.className = 'icon-button bordered danger-icon'
    remove.title = t('common.delete')
    remove.setAttribute('aria-label', `${t('common.delete')} ${profile.id}`)
    remove.innerHTML = '<i class="icon-x"></i>'
    remove.addEventListener('click', () => openDeleteProfileDialog(profile))
    actions.append(use, remove)
    card.append(copy, actions)
    return card
  }))
}

function renderProfiles(profiles) {
  state.profiles = profiles
  const selected = $('#voice-profile').value
  populateSelect($('#voice-profile'), profiles.map((profile) => ({ value: profile.id, label: profile.id })), selected)
  $('#profile-count').textContent = String(profiles.length)
  renderProfileList()
  updateProfileNamePreview()
}

async function refreshProfiles() {
  const payload = await fetchJson('/tts/voice-profiles')
  renderProfiles(payload.data || [])
}

$('#voice-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const form = event.currentTarget
  const button = $('button[type="submit"]', form)
  const name = normalizedProfileName($('#profile-name').value)
  const file = profileAudio.currentFile()
  if (!name) return showToast(t('errors.profileNameRequired'))
  if (!file) return showToast(t('errors.referenceRequired'))
  button.disabled = true
  let upload = null
  try {
    upload = await uploadAudio(file)
    const payload = await fetchJson('/tts/voice-profiles', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name, upload_token: upload.token, ref_text: $('#profile-transcript').value.trim(),
        language: $('#profile-language').value, seed: Number($('#profile-seed').value),
        randomize_seed: $('#profile-randomize').checked,
      }),
    })
    form.reset()
    profileAudio.clear()
    await refreshProfiles()
    $('#voice-mode').value = 'profile'
    $('#voice-profile').value = payload.id
    updateVoiceMode()
    showToast(t('voices.savedToast', { name: payload.id }, `Saved ${payload.id}.`), 'success')
  } catch (error) {
    showToast(errorMessage(error))
    await releaseUpload(upload?.token)
  } finally {
    button.disabled = false
  }
})

async function loadProfileAudio(file) {
  if (!file) return
  try {
    await profileAudio.load(file, file.name)
  } catch (error) {
    profileAudio.clear()
    showToast(errorMessage(error))
  }
}

$('#profile-name').addEventListener('input', updateProfileNamePreview)
$('#profile-filter').addEventListener('input', renderProfileList)
$('#profile-audio').addEventListener('change', (event) => loadProfileAudio(event.target.files[0]))
for (const eventName of ['dragenter', 'dragover']) {
  $('#profile-audio-drop').addEventListener(eventName, (event) => {
    event.preventDefault()
    event.currentTarget.classList.add('dragging')
  })
}
for (const eventName of ['dragleave', 'drop']) {
  $('#profile-audio-drop').addEventListener(eventName, (event) => {
    event.preventDefault()
    event.currentTarget.classList.remove('dragging')
  })
}
$('#profile-audio-drop').addEventListener('drop', (event) => loadProfileAudio(event.dataTransfer.files[0]))

function closeDeleteProfileDialog() {
  profilePendingDelete = null
  $('#delete-profile-dialog').close()
}

$('#delete-profile-close').addEventListener('click', closeDeleteProfileDialog)
$('#delete-profile-cancel').addEventListener('click', closeDeleteProfileDialog)
$('#delete-profile-dialog').addEventListener('click', (event) => { if (event.target === event.currentTarget) closeDeleteProfileDialog() })
$('#delete-profile-dialog').addEventListener('close', () => { profilePendingDelete = null })
$('#delete-profile-confirm').addEventListener('click', async (event) => {
  if (!profilePendingDelete) return
  const profile = profilePendingDelete
  const button = event.currentTarget
  button.disabled = true
  try {
    await fetchJson(`/tts/voice-profiles/${encodeURIComponent(profile.id)}`, { method: 'DELETE' })
    closeDeleteProfileDialog()
    await refreshProfiles()
    showToast(t('voices.deleted', { name: profile.id }, `Deleted ${profile.id}.`), 'success')
  } catch (error) {
    showToast(errorMessage(error))
  } finally {
    button.disabled = false
  }
})

async function refreshApiStatus() {
  $('#api-output').textContent = t('common.loading')
  const paths = ['/tts/ping', '/v1/models', '/v1/audio/voices', '/tts/formats', '/tts/stream-formats', '/tts/ssml/capabilities']
  const values = await Promise.all(paths.map(async (path) => {
    try { return [path, await fetchJson(path)] } catch (error) { return [path, { error: errorMessage(error) }] }
  }))
  $('#api-output').textContent = JSON.stringify(Object.fromEntries(values), null, 2)
  try {
    $('#call-log-output').textContent = JSON.stringify(await fetchJson('/tts/openai-calls'), null, 2)
  } catch (error) {
    $('#call-log-output').textContent = errorMessage(error)
  }
}

async function refreshSystem() {
  const [status, settings] = await Promise.all([fetchJson('/tts/status'), fetchJson('/system/settings')])
  $('#readiness-output').textContent = JSON.stringify(status, null, 2)
  $('#system-default-summary').textContent = JSON.stringify(settings.generation_defaults || {}, null, 2)
}

$('#api-refresh').addEventListener('click', () => refreshApiStatus().catch((error) => showToast(errorMessage(error))))
$('#save-defaults').addEventListener('click', async (event) => {
  const button = event.currentTarget
  button.disabled = true
  try {
    const settings = await fetchJson('/system/settings/generation-defaults', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(controlValues()),
    })
    $('#system-default-summary').textContent = JSON.stringify(settings.generation_defaults, null, 2)
    showToast(t('system.saved'), 'success')
  } catch (error) { showToast(errorMessage(error)) } finally { button.disabled = false }
})

$('#clear-cache').addEventListener('click', async (event) => {
  const button = event.currentTarget
  button.disabled = true
  try {
    const payload = await fetchJson('/tts/cache/clear', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
    showToast(payload.msg, 'success')
    await refreshSystem()
  } catch (error) { showToast(errorMessage(error)) } finally { button.disabled = false }
})

$('#purge-models').addEventListener('click', async (event) => {
  const button = event.currentTarget
  button.disabled = true
  try {
    const payload = await fetchJson('/tts/purge', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
    showToast(`Purged ${payload.purged.length} model cache entries.`, 'success')
    await refreshSystem()
  } catch (error) { showToast(errorMessage(error)) } finally { button.disabled = false }
})

function element(tag, className, text) {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

function mergeGpuHistory(historyPayload) {
  const cutoff = Date.now() - GPU_HISTORY_RETENTION_MS
  Object.entries(historyPayload || {}).forEach(([index, incoming]) => {
    if (!Array.isArray(incoming)) return
    const byTimestamp = new Map()
    ;[...(state.gpuHistory.get(Number(index)) || []), ...incoming].forEach((sample) => {
      if (Number.isFinite(sample?.timestamp) && sample.timestamp >= cutoff) byTimestamp.set(sample.timestamp, sample)
    })
    const merged = [...byTimestamp.values()].sort((left, right) => left.timestamp - right.timestamp)
    if (merged.length) state.gpuHistory.set(Number(index), merged)
  })
  state.gpuHistory.forEach((samples, index) => {
    const recent = samples.filter((sample) => sample.timestamp >= cutoff)
    if (recent.length) state.gpuHistory.set(index, recent)
    else state.gpuHistory.delete(index)
  })
  persistGpuSession()
}

function gpuMetricMaximum(metric, gpu, history) {
  const observed = Math.max(1, ...history.map((sample) => sample[metric.key] || 0))
  if (['utilization', 'memory_utilization', 'temperature', 'fan_speed'].includes(metric.key)) return 100
  if (metric.key === 'memory_used' && Number.isFinite(gpu.memory_total)) return Math.max(1, gpu.memory_total)
  if (metric.key === 'power' && Number.isFinite(gpu.power_limit)) return Math.max(1, gpu.power_limit)
  if (metric.key === 'graphics_clock' && Number.isFinite(gpu.graphics_clock_max)) return Math.max(1, gpu.graphics_clock_max)
  if (metric.key === 'memory_clock' && Number.isFinite(gpu.memory_clock_max)) return Math.max(1, gpu.memory_clock_max)
  return Math.ceil(observed * 1.1)
}

function formatGpuMetric(metric, value) {
  if (!Number.isFinite(value)) return 'N/A'
  if (['utilization', 'memory_utilization', 'fan_speed'].includes(metric.key)) return `${Math.round(value)}%`
  if (metric.key === 'memory_used') return `${(value / 1024).toFixed(1)} GB`
  if (metric.key === 'temperature') return `${Math.round(value)} C`
  if (metric.key === 'power') return `${Math.round(value)} W`
  return `${Math.round(value)} MHz`
}

function createGpuMetricChart(metric, gpu, history, now) {
  const current = gpu[metric.key]
  if (!Number.isFinite(current)) return null
  const samples = history.filter((sample) => Number.isFinite(sample[metric.key]))
  const maximum = gpuMetricMaximum(metric, gpu, samples)
  const average = samples.length ? samples.reduce((sum, sample) => sum + sample[metric.key], 0) / samples.length : current
  const peak = samples.length ? Math.max(...samples.map((sample) => sample[metric.key])) : current
  const chart = element('div', 'gpu-metric-chart')
  chart.style.setProperty('--chart-color', metric.color)
  const scale = element('div', 'gpu-chart-scale')
  scale.append(element('span', '', metric.label), element('strong', '', formatGpuMetric(metric, current)))
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  svg.setAttribute('class', 'gpu-sparkline')
  svg.setAttribute('viewBox', '0 0 300 70')
  svg.setAttribute('preserveAspectRatio', 'none')
  svg.setAttribute('role', 'img')
  svg.setAttribute('aria-label', t('gpu.historyAria', { metric: metric.label, average: formatGpuMetric(metric, average), peak: formatGpuMetric(metric, peak) }))
  for (let column = 0; column <= 10; column += 1) {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
    line.setAttribute('class', 'gpu-grid-line'); line.setAttribute('x1', String(column * 30)); line.setAttribute('x2', String(column * 30)); line.setAttribute('y1', '0'); line.setAttribute('y2', '70'); svg.append(line)
  }
  const start = now - state.gpuWindowMs
  const points = samples.map((sample) => {
    const x = Math.min(300, Math.max(0, (sample.timestamp - start) / state.gpuWindowMs * 300))
    const y = 70 - (Math.min(maximum, Math.max(0, sample[metric.key])) / maximum * 70)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  if (samples.length > 1) {
    const list = points.split(' ')
    const area = document.createElementNS('http://www.w3.org/2000/svg', 'polygon')
    area.setAttribute('class', 'gpu-chart-area')
    area.setAttribute('points', `${list[0].split(',')[0]},70 ${points} ${list.at(-1).split(',')[0]},70`)
    svg.append(area)
  }
  const line = document.createElementNS('http://www.w3.org/2000/svg', 'polyline')
  line.setAttribute('class', 'gpu-chart-line'); line.setAttribute('points', points); svg.append(line)
  const axis = element('div', 'gpu-chart-axis')
  axis.append(element('span', '', state.gpuWindowMs === 60000 ? t('gpu.oneMinute') : t('gpu.tenMinutes')), element('span', '', t('gpu.averagePeak', { average: formatGpuMetric(metric, average), peak: formatGpuMetric(metric, peak) })))
  chart.append(scale, svg, axis)
  return chart
}

function renderGpuMonitor(gpus) {
  const monitor = element('div', 'gpu-monitor')
  const heading = element('div', 'gpu-monitor-heading')
  const windowControl = element('div', 'gpu-window-control')
  windowControl.setAttribute('role', 'group')
  windowControl.setAttribute('aria-label', t('gpu.historyWindow'))
  ;[[60000, t('gpu.oneMinute')], [600000, t('gpu.tenMinutes')]].forEach(([windowMs, label]) => {
    const button = element('button', windowMs === state.gpuWindowMs ? 'active' : '', label)
    button.type = 'button'
    button.setAttribute('aria-pressed', String(windowMs === state.gpuWindowMs))
    button.addEventListener('click', () => { state.gpuWindowMs = windowMs; persistUiSession(); renderGpuMonitor(state.gpuStats) })
    windowControl.append(button)
  })
  heading.append(element('div', 'gpu-monitor-title', t('gpu.monitor')), windowControl)
  monitor.append(heading)
  if (!gpus.length) {
    monitor.append(element('div', 'gpu-monitor-muted', t('gpu.unavailable')))
    $('#gpu-output').replaceChildren(monitor)
    return
  }
  const grid = element('div', 'gpu-card-grid')
  gpus.forEach((gpu) => {
    const now = Date.now()
    const history = (state.gpuHistory.get(gpu.index) || []).filter((sample) => sample.timestamp >= now - state.gpuWindowMs)
    const card = element('div', 'gpu-card')
    const head = element('div', 'gpu-card-head')
    head.append(element('strong', '', `GPU ${gpu.index}`), element('span', '', gpu.name))
    const metrics = element('div', 'gpu-metrics-grid')
    GPU_METRICS.forEach((metric) => { const chart = createGpuMetricChart(metric, gpu, history, now); if (chart) metrics.append(chart) })
    const details = element('div', 'gpu-live-details')
    if (gpu.performance_state) details.append(element('span', '', t('gpu.state', { state: gpu.performance_state })))
    if (Number.isFinite(gpu.pcie_generation) && Number.isFinite(gpu.pcie_width)) details.append(element('span', '', t('gpu.pcie', { generation: gpu.pcie_generation, width: gpu.pcie_width })))
    if (Number.isFinite(gpu.power_limit)) details.append(element('span', '', t('gpu.powerLimit', { power: Math.round(gpu.power_limit) })))
    card.append(head, metrics, details); grid.append(card)
  })
  monitor.append(grid)
  $('#gpu-output').replaceChildren(monitor)
}

async function refreshGpuMonitor() {
  if (state.gpuRefreshActive) return
  state.gpuRefreshActive = true
  try {
    const payload = await fetchJson('/system/gpu')
    state.gpuStats = Array.isArray(payload.gpus) ? payload.gpus : []
    mergeGpuHistory(payload.history)
    renderGpuMonitor(state.gpuStats)
  } catch { renderGpuMonitor(state.gpuStats) } finally { state.gpuRefreshActive = false }
}

function startGpuMonitor() {
  if (state.gpuTimer || document.hidden) return
  if (state.gpuStats.length) renderGpuMonitor(state.gpuStats)
  refreshGpuMonitor()
  state.gpuTimer = setInterval(refreshGpuMonitor, GPU_POLL_INTERVAL_MS)
}

function stopGpuMonitor() { clearInterval(state.gpuTimer); state.gpuTimer = null }

async function pollReadiness() {
  const badge = $('#runtime-badge')
  try {
    const status = await fetchJson('/tts/status')
    state.backendReady = true
    badge.dataset.state = 'ready'
    badge.querySelector('strong').textContent = t('runtime.ready')
    $('#runtime-model').textContent = `${status.model} · ${status.resolved_device}`
    badge.title = status.runtime
    if ($('#global-status').textContent === t('status.connecting')) setStatus(t('status.ready'), 'success')
  } catch {
    state.backendReady = false
    badge.dataset.state = 'starting'
    badge.querySelector('strong').textContent = t('runtime.starting')
    $('#runtime-model').textContent = t('runtime.waiting')
  }
  setTimeout(pollReadiness, state.backendReady ? 15000 : 3000)
}

async function loadWorkspace() {
  const [defaults, status, languages, formats, design, settings, profiles] = await Promise.all([
    fetchJson('/tts/defaults'), fetchJson('/tts/status'), fetchJson('/tts/languages'), fetchJson('/tts/formats'),
    fetchJson('/tts/voice-design/options'), fetchJson('/system/settings'), fetchJson('/tts/voice-profiles'),
  ])
  const languageRows = languages.languages
    || (languages.language_names || []).map((name) => ({ id: '', name }))
  const languageOptions = [
    { value: '', label: t('common.auto', {}, 'Auto') },
    ...languageRows
      .map(({ id, name }) => ({ value: name, label: nativeLanguageLabel(id, name) }))
      .sort((left, right) => left.label.localeCompare(right.label, browserLanguage())),
  ]
  populateSelect($('#language'), languageOptions)
  populateSelect($('#profile-language'), languageOptions)
  const devices = [{ value: 'auto', label: 'Auto' }, { value: 'cpu', label: 'CPU' }]
  ;(status.cuda_memory || []).forEach((gpu) => devices.push({ value: gpu.device, label: `${gpu.device} · ${gpu.name}` }))
  populateSelect($('#device'), devices, defaults.device || 'auto')
  populateSelect($('#output-format'), Object.entries(formats.formats || {}).map(([value, config]) => ({ value, label: config.label || value.toUpperCase() })), 'mp3')
  ;(design.categories || []).forEach((category) => {
    const select = $(`[data-design="${category.id}"]`)
    if (!select) return
    populateSelect(select, [{ value: '', label: t('design.noPreference') }, ...category.options.map((value) => ({ value, label: value }))])
  })
  renderProfiles(profiles.data || [])
  applyControlValues(settings.generation_defaults || DEFAULT_CONTROLS)
  $('#text-input').value = state.inputType === 'text' ? t('composer.defaultText') : samplesForInputType(state.inputType)[0]
  setInputType(state.inputType, { replaceKnownSample: false, persist: false })
  $('#reference-audio-name').textContent = 'WAV, MP3, FLAC, OGG, or M4A'
}

$('#voice-mode').addEventListener('change', updateVoiceMode)
$$('[data-input-type]').forEach((button) => button.addEventListener('click', () => setInputType(button.dataset.inputType)))
$('#text-input').addEventListener('input', () => { updateTextMetrics(); scheduleNormalizationPreview() })
$('#language').addEventListener('change', scheduleNormalizationPreview)
$('#normalize-text').addEventListener('change', scheduleNormalizationPreview)
$('#sample-button').addEventListener('click', () => {
  const current = $('#text-input').value
  const samples = samplesForInputType()
  const candidates = samples.filter((sample) => sample !== current)
  $('#text-input').value = candidates[Math.floor(Math.random() * candidates.length)] || samples[0]
  updateTextMetrics()
  scheduleNormalizationPreview()
})
$('#reference-audio').addEventListener('change', (event) => { $('#reference-audio-name').textContent = event.target.files[0]?.name || 'WAV, MP3, FLAC, OGG, or M4A' })
$('#reset-controls').addEventListener('click', () => applyControlValues(DEFAULT_CONTROLS))
$('#expression-guide-button').addEventListener('click', () => $('#expression-guide').showModal())
$('#expression-guide-close').addEventListener('click', () => $('#expression-guide').close())
$('#expression-guide').addEventListener('click', (event) => { if (event.target === event.currentTarget) event.currentTarget.close() })

document.addEventListener('visibilitychange', () => {
  if (document.hidden) stopGpuMonitor()
  else if (state.activeTab === 'system') startGpuMonitor()
})
window.addEventListener('beforeunload', () => {
  stopGpuMonitor()
  state.normalizationAbort?.abort()
  state.streamAbort?.abort()
  state.streamPlayback?.stop()
  generateOutput.destroy()
  streamOutput.destroy()
  profileAudio.destroy()
})

restoreSessionState()
bindRangePairs()
setHeroCollapsed(state.headerCollapsed, false, false)
activateTab(state.activeTab)
loadWorkspace().then(() => setStatus(t('status.ready'), 'success')).catch((error) => {
  setStatus(t('status.failed'), 'error')
  showToast(errorMessage(error))
})
pollReadiness()
