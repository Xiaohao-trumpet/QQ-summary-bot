package com.summarybot.collector

import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.EditText
import android.widget.RadioGroup
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.summarybot.collector.data.SettingsStore
import com.summarybot.collector.worker.FlushQueueWorker

class MainActivity : AppCompatActivity() {
    private lateinit var settingsStore: SettingsStore

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        settingsStore = SettingsStore(this)

        val serverUrl = findViewById<EditText>(R.id.serverUrlInput)
        val token = findViewById<EditText>(R.id.tokenInput)
        val deviceName = findViewById<EditText>(R.id.deviceNameInput)
        val allowedGroups = findViewById<EditText>(R.id.allowedGroupsInput)
        val filterMode = findViewById<RadioGroup>(R.id.filterModeGroup)
        val deviceIdView = findViewById<TextView>(R.id.deviceIdValue)
        val statusView = findViewById<TextView>(R.id.statusValue)
        val openSettingsButton = findViewById<Button>(R.id.openNotificationAccessButton)
        val saveButton = findViewById<Button>(R.id.saveConfigButton)
        val syncButton = findViewById<Button>(R.id.syncNowButton)

        val config = settingsStore.load()
        serverUrl.setText(config.serverUrl)
        token.setText(config.collectorToken)
        deviceName.setText(config.deviceName)
        allowedGroups.setText(config.allowedGroups.joinToString(","))
        filterMode.check(
            if (config.groupFilterMode == "contains") R.id.filterContains else R.id.filterExact
        )
        deviceIdView.text = config.deviceId
        statusView.text = getString(R.string.status_not_granted)

        openSettingsButton.setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }

        saveButton.setOnClickListener {
            val updated = config.copy(
                serverUrl = serverUrl.text.toString().trim(),
                collectorToken = token.text.toString().trim(),
                deviceName = deviceName.text.toString().trim().ifBlank { android.os.Build.MODEL },
                allowedGroups = allowedGroups.text.toString()
                    .split(",")
                    .map { it.trim() }
                    .filter { it.isNotBlank() },
                groupFilterMode = if (filterMode.checkedRadioButtonId == R.id.filterContains) "contains" else "exact",
            )
            settingsStore.save(updated)
            statusView.text = getString(R.string.status_saved)
        }

        syncButton.setOnClickListener {
            WorkManager.getInstance(this).enqueueUniqueWork(
                FlushQueueWorker.ONE_TIME_SYNC_NAME,
                ExistingWorkPolicy.REPLACE,
                OneTimeWorkRequestBuilder<FlushQueueWorker>().build()
            )
            statusView.text = getString(R.string.status_sync_requested)
        }
    }
}
