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
            isLoading.value = true
            const inbox = await apiService.getNotificationInbox()
            pendingReviewCount.value = inbox.due_count || 0
            riskAlertCount.value = inbox.risk_alert_count || 0
        } catch (error) {
            console.error('Failed to check notifications:', error)
        } finally {
            isLoading.value = false
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
