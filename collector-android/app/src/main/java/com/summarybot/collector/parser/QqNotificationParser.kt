package com.summarybot.collector.parser

import android.app.Notification
import android.service.notification.StatusBarNotification
import com.summarybot.collector.data.CollectorConfig
import com.summarybot.collector.data.CollectorEvent
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.UUID

data class ParsedNotification(
    val groupName: String,
    val senderName: String,
    val content: String,
    val rawTitle: String,
    val rawText: String,
    val rawSubtext: String,
)

class QqNotificationParser {
    fun parse(sbn: StatusBarNotification, config: CollectorConfig): CollectorEvent? {
        if (sbn.packageName != QQ_PACKAGE_NAME) {
            return null
        }
        val extras = sbn.notification.extras
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()?.trim().orEmpty()
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()?.trim().orEmpty()
        val subText = extras.getCharSequence(Notification.EXTRA_SUB_TEXT)?.toString()?.trim().orEmpty()
        val bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()?.trim().orEmpty()
        val body = bigText.ifBlank { text }
        val parsed = parsePayload(title, body, subText, config) ?: return null

        val mentionedMe = body.contains("@我") || body.contains("有人@你")
        return CollectorEvent(
            eventId = UUID.randomUUID().toString(),
            sourceType = "android_notification",
            sourceApp = sbn.packageName,
            groupName = parsed.groupName,
            senderName = parsed.senderName,
            content = parsed.content,
            timestamp = OffsetDateTime.ofInstant(
                java.time.Instant.ofEpochMilli(sbn.postTime),
                ZoneId.systemDefault()
            ).format(DateTimeFormatter.ISO_OFFSET_DATE_TIME),
            mentionedMe = mentionedMe,
            rawTitle = parsed.rawTitle,
            rawText = parsed.rawText,
            rawSubtext = parsed.rawSubtext,
        )
    }

    private fun parsePayload(
        title: String,
        body: String,
        subText: String,
        config: CollectorConfig,
    ): ParsedNotification? {
        if (title.isBlank() || body.isBlank()) return null

        val senderAndBody = splitSenderAndBody(body)
        if (senderAndBody != null) {
            val groupName = normalizeGroupName(title)
            if (!isGroupAllowed(groupName, config)) return null
            return ParsedNotification(
                groupName = groupName,
                senderName = senderAndBody.first,
                content = senderAndBody.second,
                rawTitle = title,
                rawText = body,
                rawSubtext = subText,
            )
        }

        val summaryGroup = extractGroupFromSummary(title)
        if (summaryGroup != null) {
            if (!isGroupAllowed(summaryGroup.first, config)) return null
            return ParsedNotification(
                groupName = summaryGroup.first,
                senderName = summaryGroup.second,
                content = body,
                rawTitle = title,
                rawText = body,
                rawSubtext = subText,
            )
        }
        return null
    }

    private fun splitSenderAndBody(body: String): Pair<String, String>? {
        val separator = if (body.contains("：")) "：" else if (body.contains(":")) ":" else null
        if (separator == null) return null
        val parts = body.split(separator, limit = 2)
        if (parts.size != 2) return null
        val sender = parts[0].trim()
        val content = parts[1].trim()
        if (sender.isBlank() || content.isBlank()) return null
        return sender to content
    }

    private fun extractGroupFromSummary(title: String): Pair<String, String>? {
        val cleaned = normalizeGroupName(title)
        val openIndex = cleaned.indexOf('（').takeIf { it >= 0 } ?: cleaned.indexOf('(').takeIf { it >= 0 } ?: -1
        val closeIndex = cleaned.indexOf('）').takeIf { it > openIndex } ?: cleaned.indexOf(')').takeIf { it > openIndex } ?: -1
        if (openIndex > 0 && closeIndex > openIndex) {
            return cleaned.substring(0, openIndex).trim() to cleaned.substring(openIndex + 1, closeIndex).trim()
        }
        return null
    }

    private fun isGroupAllowed(groupName: String, config: CollectorConfig): Boolean {
        if (config.allowedGroups.isEmpty()) return true
        return if (config.groupFilterMode == "contains") {
            config.allowedGroups.any { groupName.contains(it) || it.contains(groupName) }
        } else {
            config.allowedGroups.any { normalizeGroupName(it) == normalizeGroupName(groupName) }
        }
    }

    private fun normalizeGroupName(value: String): String {
        return value.replace(Regex("\\s*[（(]\\d+(条新消息)?[)）]\\s*$"), "").trim()
    }

    companion object {
        private const val QQ_PACKAGE_NAME = "com.tencent.mobileqq"
    }
}
