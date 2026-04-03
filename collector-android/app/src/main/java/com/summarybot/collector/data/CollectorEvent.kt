package com.summarybot.collector.data

import org.json.JSONObject

data class CollectorEvent(
    val eventId: String,
    val sourceType: String,
    val sourceApp: String,
    val groupName: String,
    val senderName: String,
    val content: String,
    val timestamp: String,
    val mentionedMe: Boolean,
    val rawTitle: String,
    val rawText: String,
    val rawSubtext: String,
) {
    fun toJson(): JSONObject = JSONObject()
        .put("event_id", eventId)
        .put("source_type", sourceType)
        .put("source_app", sourceApp)
        .put("group_name", groupName)
        .put("sender_name", senderName)
        .put("content", content)
        .put("timestamp", timestamp)
        .put("mentioned_me", mentionedMe)
        .put("raw_title", rawTitle)
        .put("raw_text", rawText)
        .put("raw_subtext", rawSubtext)
        .put("metadata", JSONObject())

    companion object {
        fun fromJson(json: JSONObject): CollectorEvent {
            return CollectorEvent(
                eventId = json.getString("event_id"),
                sourceType = json.getString("source_type"),
                sourceApp = json.getString("source_app"),
                groupName = json.getString("group_name"),
                senderName = json.getString("sender_name"),
                content = json.getString("content"),
                timestamp = json.getString("timestamp"),
                mentionedMe = json.optBoolean("mentioned_me", false),
                rawTitle = json.optString("raw_title", ""),
                rawText = json.optString("raw_text", ""),
                rawSubtext = json.optString("raw_subtext", ""),
            )
        }
    }
}
