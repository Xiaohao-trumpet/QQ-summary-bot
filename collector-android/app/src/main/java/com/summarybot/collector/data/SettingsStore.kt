package com.summarybot.collector.data

import android.content.Context
import android.os.Build
import java.util.UUID

class SettingsStore(context: Context) {
    private val prefs = context.getSharedPreferences("summary_bot_collector", Context.MODE_PRIVATE)

    fun load(): CollectorConfig {
        val deviceId = prefs.getString(KEY_DEVICE_ID, null) ?: UUID.randomUUID().toString().also {
            prefs.edit().putString(KEY_DEVICE_ID, it).apply()
        }
        return CollectorConfig(
            deviceId = deviceId,
            deviceName = prefs.getString(KEY_DEVICE_NAME, Build.MODEL).orEmpty(),
            serverUrl = prefs.getString(KEY_SERVER_URL, "").orEmpty(),
            collectorToken = prefs.getString(KEY_COLLECTOR_TOKEN, "").orEmpty(),
            allowedGroups = prefs.getString(KEY_ALLOWED_GROUPS, "").orEmpty()
                .split(",")
                .map { it.trim() }
                .filter { it.isNotBlank() },
            groupFilterMode = prefs.getString(KEY_GROUP_FILTER_MODE, "exact").orEmpty(),
        )
    }

    fun save(config: CollectorConfig) {
        prefs.edit()
            .putString(KEY_DEVICE_ID, config.deviceId)
            .putString(KEY_DEVICE_NAME, config.deviceName)
            .putString(KEY_SERVER_URL, config.serverUrl)
            .putString(KEY_COLLECTOR_TOKEN, config.collectorToken)
            .putString(KEY_ALLOWED_GROUPS, config.allowedGroups.joinToString(","))
            .putString(KEY_GROUP_FILTER_MODE, config.groupFilterMode)
            .apply()
    }

    companion object {
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_DEVICE_NAME = "device_name"
        private const val KEY_SERVER_URL = "server_url"
        private const val KEY_COLLECTOR_TOKEN = "collector_token"
        private const val KEY_ALLOWED_GROUPS = "allowed_groups"
        private const val KEY_GROUP_FILTER_MODE = "group_filter_mode"
    }
}
