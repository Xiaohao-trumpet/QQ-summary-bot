package com.summarybot.collector.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.summarybot.collector.data.EventQueueStore
import com.summarybot.collector.data.SettingsStore
import com.summarybot.collector.network.CollectorApiClient

class FlushQueueWorker(
    appContext: Context,
    workerParams: WorkerParameters,
) : CoroutineWorker(appContext, workerParams) {
    private val settingsStore = SettingsStore(appContext)
    private val queueStore = EventQueueStore(appContext)
    private val apiClient = CollectorApiClient()

    override suspend fun doWork(): Result {
        val config = settingsStore.load()
        if (config.serverUrl.isBlank() || config.collectorToken.isBlank()) {
            return Result.success()
        }

        val pending = queueStore.peek(limit = 30)
        if (pending.isEmpty()) {
            apiClient.sendHeartbeat(config)
            return Result.success()
        }

        val success = apiClient.sendEvents(config, pending)
        return if (success) {
            queueStore.remove(pending.map { it.eventId }.toSet())
            Result.success()
        } else {
            Result.retry()
        }
    }

    companion object {
        const val UNIQUE_WORK_NAME = "summary_bot_periodic_flush"
        const val ONE_TIME_SYNC_NAME = "summary_bot_one_time_flush"
    }
}
