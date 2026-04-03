package com.summarybot.collector.service

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.summarybot.collector.data.EventQueueStore
import com.summarybot.collector.data.SettingsStore
import com.summarybot.collector.parser.QqNotificationParser
import com.summarybot.collector.worker.FlushQueueWorker

class QqNotificationListenerService : NotificationListenerService() {
    private lateinit var settingsStore: SettingsStore
    private lateinit var queueStore: EventQueueStore
    private val parser = QqNotificationParser()

    override fun onCreate() {
        super.onCreate()
        settingsStore = SettingsStore(this)
        queueStore = EventQueueStore(this)
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val config = settingsStore.load()
        val event = parser.parse(sbn, config) ?: return
        queueStore.enqueue(event)
        WorkManager.getInstance(this).enqueueUniqueWork(
            FlushQueueWorker.ONE_TIME_SYNC_NAME,
            ExistingWorkPolicy.REPLACE,
            OneTimeWorkRequestBuilder<FlushQueueWorker>().build()
        )
    }
}
