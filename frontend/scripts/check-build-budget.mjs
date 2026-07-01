import { promises as fs } from 'node:fs'
import path from 'node:path'

const rootDir = path.resolve(process.cwd())
const assetsDir = path.join(rootDir, 'dist', 'assets')

const BUDGETS = {
  maxEntryJsGzipKb: 180,
  maxInitialVendorJsKb: 450,
  forbidEchartsInEntry: true,
}

async function readAssets() {
  const files = await fs.readdir(assetsDir)
  const jsFiles = files.filter((name) => name.endsWith('.js'))
  const entries = await Promise.all(
    jsFiles.map(async (name) => {
      const fullPath = path.join(assetsDir, name)
      const stat = await fs.stat(fullPath)
      return { name, bytes: stat.size, kb: Number((stat.size / 1024).toFixed(2)) }
    }),
  )
  entries.sort((a, b) => b.bytes - a.bytes)
  return entries
}

function findEntryChunk(entries) {
  return entries.find((item) => /^index-.*\.js$/.test(item.name))
}

function initialVendorChunks(entries) {
  return entries.filter((item) =>
    /^vendor-(vue|axios|naive-ui|markdown)-.*\.js$/.test(item.name),
  )
}

async function main() {
  const entries = await readAssets()
  const entry = findEntryChunk(entries)
  const vendors = initialVendorChunks(entries)
  const echartsChunk = entries.find((item) => item.name.includes('vendor-echarts'))

  const failures = []

  if (!entry) {
    failures.push('missing index-*.js entry chunk')
  } else if (entry.kb > BUDGETS.maxEntryJsGzipKb * 2.8) {
    // dist is unminified-gzip proxy: use raw kb threshold ~2.8x gzip budget
    failures.push(`entry chunk too large: ${entry.name} ${entry.kb} KB`)
  }

  const vendorKb = vendors.reduce((sum, item) => sum + item.kb, 0)
  if (vendorKb > BUDGETS.maxInitialVendorJsKb * 2.8) {
    failures.push(`initial vendor chunks too large: ${vendorKb.toFixed(1)} KB`)
  }

  if (BUDGETS.forbidEchartsInEntry && entry) {
    const entrySource = await fs.readFile(path.join(assetsDir, entry.name), 'utf-8')
    if (/echarts\/charts|vendor-echarts/.test(entrySource)) {
      failures.push('entry chunk statically references echarts')
    }
  }

  console.log('[build-budget] entry:', entry ? `${entry.name} (${entry.kb} KB)` : 'missing')
  console.log('[build-budget] initial vendors kb:', vendorKb.toFixed(1))
  console.log('[build-budget] echarts chunk:', echartsChunk ? `${echartsChunk.name} (${echartsChunk.kb} KB)` : 'not built')

  if (failures.length > 0) {
    console.error('[build-budget] FAILED:')
    for (const failure of failures) {
      console.error(`  - ${failure}`)
    }
    process.exit(1)
  }

  console.log('[build-budget] passed')
}

main().catch((error) => {
  console.error('[build-budget] failed:', error)
  process.exit(1)
})
