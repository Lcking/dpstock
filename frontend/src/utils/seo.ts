type MetaAttr = 'name' | 'property'

interface PageSeoOptions {
  title: string
  description: string
  canonicalPath?: string
  keywords?: string
  robots?: string
  ogType?: string
  image?: string
}

const SITE_NAME = 'Agu AI'
const SITE_URL = 'https://aguai.net'
const DEFAULT_IMAGE = `${SITE_URL}/favicon.ico`

function ensureMetaTag(key: string, attr: MetaAttr = 'name') {
  let el = document.head.querySelector(`meta[${attr}="${key}"]`) as HTMLMetaElement | null
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, key)
    document.head.appendChild(el)
  }
  return el
}

function ensureLinkTag(rel: string) {
  let el = document.head.querySelector(`link[rel="${rel}"]`) as HTMLLinkElement | null
  if (!el) {
    el = document.createElement('link')
    el.setAttribute('rel', rel)
    document.head.appendChild(el)
  }
  return el
}

function normalizeCanonicalPath(path = '/') {
  if (!path || path === '/') return `${SITE_URL}/`
  return `${SITE_URL}${path.startsWith('/') ? path : `/${path}`}`
}

export function setCanonicalUrl(path = '/') {
  const canonical = ensureLinkTag('canonical')
  canonical.setAttribute('href', normalizeCanonicalPath(path))
}

export function applyPageSeo({
  title,
  description,
  canonicalPath = '/',
  keywords,
  robots = 'index, follow',
  ogType = 'website',
  image = DEFAULT_IMAGE,
}: PageSeoOptions) {
  document.title = title

  ensureMetaTag('description').setAttribute('content', description)
  ensureMetaTag('robots').setAttribute('content', robots)
  ensureMetaTag('og:title', 'property').setAttribute('content', title)
  ensureMetaTag('og:description', 'property').setAttribute('content', description)
  ensureMetaTag('og:type', 'property').setAttribute('content', ogType)
  ensureMetaTag('og:url', 'property').setAttribute('content', normalizeCanonicalPath(canonicalPath))
  ensureMetaTag('og:site_name', 'property').setAttribute('content', SITE_NAME)
  ensureMetaTag('og:image', 'property').setAttribute('content', image)
  ensureMetaTag('twitter:card').setAttribute('content', 'summary_large_image')
  ensureMetaTag('twitter:title').setAttribute('content', title)
  ensureMetaTag('twitter:description').setAttribute('content', description)
  ensureMetaTag('twitter:image').setAttribute('content', image)

  if (keywords) {
    ensureMetaTag('keywords').setAttribute('content', keywords)
  }

  setCanonicalUrl(canonicalPath)
}

function stripRichText(text: string) {
  return text
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/!\[[^\]]*\]\([^)]+\)/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/[#>*_\-]+/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function getJsonSummary(raw: string) {
  try {
    const parsed = JSON.parse(raw)
    const candidates = [
      parsed?.summary,
      parsed?.executive_summary,
      parsed?.conclusion,
      parsed?.analysis_summary,
      parsed?.structure_snapshot?.trend_description,
      parsed?.relative_strength?.summary,
      parsed?.capital_flow?.summary,
      parsed?.events?.summary,
    ]
    const firstText = candidates.find((item) => typeof item === 'string' && item.trim())
    if (firstText) return stripRichText(firstText)
  } catch {
    return ''
  }
  return ''
}

export function getArticlePreview(content: string, maxLength = 120) {
  const normalized = content?.trim() || ''
  if (!normalized) return '查看这篇 AI 深度分析，快速了解标的结构、强弱与风险线索。'

  const summary = normalized.startsWith('{') ? getJsonSummary(normalized) : stripRichText(normalized)
  const safeSummary = summary || '查看这篇 AI 深度分析，快速了解标的结构、强弱与风险线索。'

  if (safeSummary.length <= maxLength) return safeSummary
  return `${safeSummary.slice(0, maxLength).trim()}…`
}
