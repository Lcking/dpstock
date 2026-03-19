import { promises as fs } from 'node:fs'
import path from 'node:path'

const rootDir = path.resolve(process.cwd())
const assetsDir = path.join(rootDir, 'dist', 'assets')
const metricsDir = path.join(rootDir, 'build-metrics')

async function readAssets() {
  const files = await fs.readdir(assetsDir)
  const jsFiles = files.filter((name) => name.endsWith('.js'))

  const entries = await Promise.all(
    jsFiles.map(async (name) => {
      const fullPath = path.join(assetsDir, name)
      const stat = await fs.stat(fullPath)
      return {
        name,
        bytes: stat.size,
        kb: Number((stat.size / 1024).toFixed(2)),
      }
    }),
  )

  entries.sort((a, b) => b.bytes - a.bytes)
  return entries
}

function summarize(entries) {
  const totalBytes = entries.reduce((sum, item) => sum + item.bytes, 0)
  const warningChunks = entries.filter((item) => item.bytes > 500 * 1024)
  return {
    total_js_files: entries.length,
    total_js_bytes: totalBytes,
    total_js_kb: Number((totalBytes / 1024).toFixed(2)),
    warning_chunks: warningChunks,
    top10: entries.slice(0, 10),
  }
}

async function main() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
  const entries = await readAssets()
  const summary = summarize(entries)

  const payload = {
    generated_at: new Date().toISOString(),
    assets_dir: assetsDir,
    summary,
    files: entries,
  }

  await fs.mkdir(metricsDir, { recursive: true })
  await fs.writeFile(path.join(metricsDir, 'latest.json'), JSON.stringify(payload, null, 2), 'utf-8')
  await fs.writeFile(path.join(metricsDir, `snapshot-${timestamp}.json`), JSON.stringify(payload, null, 2), 'utf-8')

  console.log('[build-metrics] total_js_files:', summary.total_js_files)
  console.log('[build-metrics] total_js_kb:', summary.total_js_kb)
  if (summary.warning_chunks.length > 0) {
    console.log('[build-metrics] chunks_over_500kb:')
    for (const chunk of summary.warning_chunks) {
      console.log(`  - ${chunk.name}: ${chunk.kb} KB`)
    }
  } else {
    console.log('[build-metrics] no chunk over 500KB')
  }
}

main().catch((error) => {
  console.error('[build-metrics] failed:', error)
  process.exit(1)
})
