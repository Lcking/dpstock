/**
 * Smoke test: homepage must boot without white screen after echarts lazy-load.
 *
 * Usage (after `npm run build && npm run preview`):
 *   node scripts/smoke-homepage-boot.mjs --base-url http://127.0.0.1:4173
 */
import { chromium } from 'playwright'
import { readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const frontendRoot = path.resolve(__dirname, '..')

function parseBaseUrl() {
  const idx = process.argv.indexOf('--base-url')
  if (idx >= 0 && process.argv[idx + 1]) return process.argv[idx + 1]
  return 'http://127.0.0.1:4173'
}

function assertBootAssets() {
  const html = readFileSync(path.join(frontendRoot, 'dist', 'index.html'), 'utf-8')
  if (/vendor-echarts/i.test(html)) {
    throw new Error('index.html preloads vendor-echarts on first paint')
  }
  const assetsDir = path.join(frontendRoot, 'dist', 'assets')
  const indexChunk = readdirSync(assetsDir).find((name) => name.startsWith('index-') && name.endsWith('.js'))
  if (!indexChunk) throw new Error('index chunk missing in dist/assets')
  const indexSource = readFileSync(path.join(assetsDir, indexChunk), 'utf-8')
  if (/echarts\/charts|vendor-echarts/.test(indexSource)) {
    throw new Error(`${indexChunk} still references echarts on critical path`)
  }
  const homeChunk = readdirSync(assetsDir).find((name) => name.startsWith('StockAnalysisApp-') && name.endsWith('.js'))
  if (homeChunk) {
    const homeSource = readFileSync(path.join(assetsDir, homeChunk), 'utf-8')
    if (/from"echarts\/|from 'echarts\/|import\("echarts\//.test(homeSource)) {
      throw new Error(`${homeChunk} statically imports echarts into homepage route chunk`)
    }
  }
}

async function smokeBrowser(baseUrl) {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  const consoleErrors = []
  const pageErrors = []

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text())
  })
  page.on('pageerror', (error) => pageErrors.push(String(error)))

  for (let i = 0; i < 3; i += 1) {
    await page.goto(`${baseUrl}/`, { waitUntil: 'networkidle', timeout: 20000 })
    await page.waitForTimeout(500)
  }

  const state = await page.evaluate(() => {
    const app = document.querySelector('#app')
    const text = (document.body?.innerText || '').trim()
    const scripts = [...document.querySelectorAll('script[src]')].map((node) => node.src)
    return {
      title: document.title,
      appChildren: app?.children?.length || 0,
      textLength: text.length,
      hasNav: !!document.querySelector('nav, .nav-shell, a[href="/analysis"]'),
      hasHeading: !!document.querySelector('h1, h2'),
      scripts,
      loadedEcharts: scripts.some((src) => /vendor-echarts|echarts/i.test(src)),
    }
  })

  await browser.close()

  const chunkErrors = [...consoleErrors, ...pageErrors].filter((line) =>
    /ChunkLoadError|Failed to fetch dynamically imported module|Importing a module script failed/i.test(line),
  )

  if (chunkErrors.length > 0) {
    throw new Error(`chunk load errors detected: ${chunkErrors.join(' | ')}`)
  }
  if (state.appChildren < 1 || state.textLength < 100) {
    throw new Error(`homepage looks blank: ${JSON.stringify(state)}`)
  }
  if (!state.hasNav || !state.hasHeading) {
    throw new Error(`homepage shell missing: ${JSON.stringify(state)}`)
  }
  if (state.loadedEcharts) {
    throw new Error(`echarts loaded on homepage first paint: ${state.scripts.join(', ')}`)
  }

  return state
}

async function main() {
  const baseUrl = parseBaseUrl()
  assertBootAssets()
  const state = await smokeBrowser(baseUrl)
  console.log('[smoke-homepage-boot] OK')
  console.log(JSON.stringify(state, null, 2))
}

main().catch((error) => {
  console.error('[smoke-homepage-boot] FAILED:', error.message || error)
  process.exit(1)
})
