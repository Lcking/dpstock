import type { App } from 'vue'
import type { Router } from 'vue-router'
import { createDiscreteApi } from 'naive-ui'

const { message, dialog } = createDiscreteApi(['message', 'dialog'])

const CHUNK_RELOAD_PREFIX = 'aguai:chunk-reload:'
const GENERIC_ERROR_FLAG = 'aguai:runtime-error-shown'

function getErrorMessage(error: unknown): string {
  if (typeof error === 'string') return error
  if (error && typeof error === 'object' && 'message' in error) {
    const value = (error as { message?: unknown }).message
    return typeof value === 'string' ? value : String(value ?? '')
  }
  return String(error ?? '')
}

export function isChunkLoadError(error: unknown): boolean {
  const msg = getErrorMessage(error)
  return [
    /Failed to fetch dynamically imported module/i,
    /Importing a module script failed/i,
    /Loading chunk [\w-]+ failed/i,
    /ChunkLoadError/i,
    /Unable to preload CSS/i,
  ].some((pattern) => pattern.test(msg))
}

function reloadOncePerPath(reason: string): boolean {
  const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`
  const key = `${CHUNK_RELOAD_PREFIX}${currentPath}`

  if (sessionStorage.getItem(key) === '1') {
    return false
  }

  sessionStorage.setItem(key, '1')
  message.warning(reason)
  window.setTimeout(() => {
    window.location.reload()
  }, 600)
  return true
}

function showRecoveryDialog() {
  dialog.warning({
    title: '页面需要刷新',
    content: '检测到前端资源已更新或加载异常。为保证可用性，请刷新页面后重试。',
    positiveText: '立即刷新',
    negativeText: '回到首页',
    onPositiveClick: () => window.location.reload(),
    onNegativeClick: () => {
      sessionStorage.clear()
      window.location.href = '/'
    },
  })
}

export function handleRuntimeError(error: unknown, context = 'runtime') {
  if (isChunkLoadError(error)) {
    const recovered = reloadOncePerPath('页面资源已更新，正在为你自动刷新…')
    if (!recovered) {
      showRecoveryDialog()
    }
    return
  }

  const flagKey = `${GENERIC_ERROR_FLAG}:${context}`
  if (sessionStorage.getItem(flagKey) === '1') return
  sessionStorage.setItem(flagKey, '1')
  message.error('页面刚刚出现异常，请刷新后重试。若反复出现，请稍后再试。')
}

export function installRuntimeRecovery(app: App, router: Router) {
  app.config.errorHandler = (error, instance, info) => {
    console.error('[RuntimeRecovery][VueError]', info, error, instance)
    handleRuntimeError(error, 'vue')
  }

  router.onError((error) => {
    console.error('[RuntimeRecovery][RouterError]', error)
    handleRuntimeError(error, 'router')
  })

  window.addEventListener('error', (event) => {
    if (event.error) {
      console.error('[RuntimeRecovery][WindowError]', event.error)
      handleRuntimeError(event.error, 'window')
    }
  })

  window.addEventListener('unhandledrejection', (event) => {
    console.error('[RuntimeRecovery][UnhandledRejection]', event.reason)
    handleRuntimeError(event.reason, 'promise')
  })
}
