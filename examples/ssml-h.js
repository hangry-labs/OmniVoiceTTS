const toast = document.querySelector('.toast')
let toastTimer

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function highlightTag(source) {
  const tag = source.match(/^(<\/?)([A-Za-z_][\w:.-]*)([\s\S]*?)(\/?>)$/)
  if (!tag) return escapeHtml(source)
  const attributes = tag[3]
  const attributePattern = /([A-Za-z_:][\w:.-]*)(\s*=\s*)("[^"]*"|'[^']*')/g
  let cursor = 0
  let highlighted = ''
  for (const match of attributes.matchAll(attributePattern)) {
    highlighted += escapeHtml(attributes.slice(cursor, match.index))
    highlighted += `<span class="syntax-attribute">${escapeHtml(match[1])}</span>`
    highlighted += `<span class="syntax-punctuation">${escapeHtml(match[2])}</span>`
    highlighted += `<span class="syntax-value">${escapeHtml(match[3])}</span>`
    cursor = match.index + match[0].length
  }
  highlighted += escapeHtml(attributes.slice(cursor))
  return `<span class="syntax-punctuation">${escapeHtml(tag[1])}</span>`
    + `<span class="syntax-tag">${escapeHtml(tag[2])}</span>`
    + highlighted
    + `<span class="syntax-punctuation">${escapeHtml(tag[4])}</span>`
}

function highlightSsml(source) {
  const tokenPattern = /<!--[\s\S]*?-->|<\/?[A-Za-z_][^>]*>|\[[^\]\r\n]{1,80}\]/g
  let cursor = 0
  let highlighted = ''
  for (const match of source.matchAll(tokenPattern)) {
    highlighted += escapeHtml(source.slice(cursor, match.index))
    const token = match[0]
    if (token.startsWith('<!--')) {
      highlighted += `<span class="syntax-comment">${escapeHtml(token)}</span>`
    } else if (token.startsWith('<')) {
      highlighted += highlightTag(token)
    } else {
      highlighted += `<span class="syntax-cue">${escapeHtml(token)}</span>`
    }
    cursor = match.index + token.length
  }
  return highlighted + escapeHtml(source.slice(cursor))
}

document.querySelectorAll('[id$="-source"]').forEach((source) => {
  source.innerHTML = highlightSsml(source.textContent)
})

function showToast(message) {
  window.clearTimeout(toastTimer)
  toast.textContent = message
  toast.hidden = false
  toastTimer = window.setTimeout(() => { toast.hidden = true }, 1800)
}

document.querySelectorAll('[data-copy-target]').forEach((button) => {
  button.addEventListener('click', async () => {
    const source = document.getElementById(button.dataset.copyTarget)
    try {
      await navigator.clipboard.writeText(source.textContent)
      showToast('Copied to clipboard')
    } catch {
      showToast('Clipboard access was unavailable')
    }
  })
})
