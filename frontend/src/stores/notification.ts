import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { apiService } from '@/services/api'

export const useNotificationStore = defineStore('notification', () => {
    const pendingReviewCount = ref(0)
    const riskAlertCount = ref(0)
    const isLoading = ref(false)

    let pollInterval: number | null = null

    const totalNotificationCount = computed(
        () => pendingReviewCount.value + riskAlertCount.value
    )

    async function checkReviews() {
        if (isLoading.value) return

        try {
            const [dueCount, alertCount] = await Promise.all([
                apiService.getDueCount(),
                apiService.getWatchlistRiskAlertUnreadCount(),
            ])
            pendingReviewCount.value = dueCount
            riskAlertCount.value = alertCount
        } catch (error) {
            console.error('Failed to check notifications:', error)
        }
    }

    function startPolling(intervalMs = 60000) {
        checkReviews()
        stopPolling()
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
        riskAlertCount,
        totalNotificationCount,
        checkReviews,
        startPolling,
        stopPolling
    }
})
