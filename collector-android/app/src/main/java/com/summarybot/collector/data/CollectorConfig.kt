package com.summarybot.collector.data

data class CollectorConfig(
    val deviceId: String,
    val deviceName: String,
    val platform: String = "android",
    val appVersion: String = "0.1.0",
    val serverUrl: String = "",
    val collectorToken: String = "",
    val allowedGroups: List<String> = emptyList(),
    val groupFilterMode: String = "exact"
)
