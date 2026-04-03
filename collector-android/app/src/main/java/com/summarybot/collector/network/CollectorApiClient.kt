package com.summarybot.collector.network

import com.summarybot.collector.data.CollectorConfig
import com.summarybot.collector.data.CollectorEvent
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject

class CollectorApiClient {
    private val client = OkHttpClient()

    fun sendHeartbeat(config: CollectorConfig): Boolean {
        val payload = JSONObject()
            .put("device", buildDevice(config))
        val request = Request.Builder()
            .url("${config.serverUrl.trimEnd('/')}/api/v1/collector/heartbeat")
            .header("Authorization", "Bearer ${config.collectorToken}")
            .post(payload.toString().toRequestBody(JSON_MEDIA_TYPE))
            .build()
        client.newCall(request).execute().use { response ->
            return response.isSuccessful
        }
    }

    fun sendEvents(config: CollectorConfig, events: List<CollectorEvent>): Boolean {
        val eventArray = JSONArray()
        events.forEach { eventArray.put(it.toJson()) }
        val payload = JSONObject()
            .put("device", buildDevice(config))
            .put("events", eventArray)
        val request = Request.Builder()
            .url("${config.serverUrl.trimEnd('/')}/api/v1/collector/events")
            .header("Authorization", "Bearer ${config.collectorToken}")
            .post(payload.toString().toRequestBody(JSON_MEDIA_TYPE))
            .build()
        client.newCall(request).execute().use { response ->
            return response.isSuccessful
        }
    }

    private fun buildDevice(config: CollectorConfig): JSONObject {
        return JSONObject()
            .put("device_id", config.deviceId)
            .put("device_name", config.deviceName)
            .put("platform", config.platform)
            .put("app_version", config.appVersion)
    }

    companion object {
        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()
    }
}
