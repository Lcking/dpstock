import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiService } from '@/services/api'

export const useNotificationStore = defineStore('notification', () => {
    const pendingReviewCount = ref(0)
    const isLoading = ref(false)

    // Poll interval handle
    let pollInterval: number | null = null

    async function checkReviews() {
        if (isLoading.value) return

        try {
            // Don't set loading for background polls to avoid UI flicker
            // isLoading.value = true
            const count = await apiService.getDueCount()
            pendingReviewCount.value = count
        } catch (error) {
            console.error('Failed to check reviews:', error)
        } finally {
            // isLoading.value = false
        }
    }

    function startPolling(intervalMs = 60000) { // Default every 1 minute
        // Initial check
        checkReviews()

        // Clear existing interval if any
        stopPolling()

        // Start new interval
        pollInterval = window.setInterval(() => {
            checkReviews()
        }, intervalMs)

        console.log('[NotificationStore] Started polling every', intervalMs, 'ms')
    }

    function stopPolling() {
        if (pollInterval) {
            window.clearInterval(pollInterval)
            pollInterval = null
        }
    }

    return {
        pendingReviewCount,
        checkReviews,
        startPolling,
        stopPolling
    }
})
