package com.summarybot.collector.data

import android.content.Context
import org.json.JSONArray

class EventQueueStore(context: Context) {
    private val prefs = context.getSharedPreferences("summary_bot_queue", Context.MODE_PRIVATE)

    @Synchronized
    fun enqueue(event: CollectorEvent) {
        val array = JSONArray(prefs.getString(KEY_PENDING_EVENTS, "[]"))
        array.put(event.toJson())
        prefs.edit().putString(KEY_PENDING_EVENTS, array.toString()).apply()
    }

    @Synchronized
    fun peek(limit: Int = 30): List<CollectorEvent> {
        val array = JSONArray(prefs.getString(KEY_PENDING_EVENTS, "[]"))
        return buildList {
            for (index in 0 until minOf(limit, array.length())) {
                add(CollectorEvent.fromJson(array.getJSONObject(index)))
            }
        }
    }

    @Synchronized
    fun remove(eventIds: Set<String>) {
        val array = JSONArray(prefs.getString(KEY_PENDING_EVENTS, "[]"))
        val next = JSONArray()
        for (index in 0 until array.length()) {
            val event = array.getJSONObject(index)
            if (!eventIds.contains(event.getString("event_id"))) {
                next.put(event)
            }
        }
        prefs.edit().putString(KEY_PENDING_EVENTS, next.toString()).apply()
    }

    companion object {
        private const val KEY_PENDING_EVENTS = "pending_events"
    }
}
