package ru.sistema.player

import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import java.util.Calendar

object ReminderScheduler {
    fun schedule(context: Context, state: PlayerState) {
        val manager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val pending = pending(context)
        manager.cancel(pending)
        if (!state.reminderEnabled) return
        val calendar = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, state.reminderMinute / 60); set(Calendar.MINUTE, state.reminderMinute % 60)
            set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
            if (timeInMillis <= System.currentTimeMillis()) add(Calendar.DAY_OF_YEAR, 1)
        }
        manager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, calendar.timeInMillis, pending)
    }
    private fun pending(context: Context): PendingIntent = PendingIntent.getBroadcast(context, 90,
        Intent(context, ReminderReceiver::class.java), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
}

class ReminderReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val store = PlayerStore(context); val state = store.load()
        if (intent.action == Intent.ACTION_BOOT_COMPLETED || intent.action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            ReminderScheduler.schedule(context, state); return
        }
        val today = java.time.LocalDate.now()
        if (!state.reminderEnabled || GameEngine.isDayComplete(state, today)) {
            ReminderScheduler.schedule(context, state); return
        }
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(NotificationChannel("daily_protocol", "Ежедневный протокол", NotificationManager.IMPORTANCE_DEFAULT))
        val open = PendingIntent.getActivity(context, 91, Intent(context, MainActivity::class.java), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val done = GameEngine.completedToday(state, today).size
        val notification = android.app.Notification.Builder(context, "daily_protocol")
            .setSmallIcon(R.drawable.ic_launcher).setContentTitle("СИСТЕМА · протокол не завершён")
            .setContentText("Выполнено $done из 6. Выбери следующее реальное действие.")
            .setContentIntent(open).setAutoCancel(true).build()
        manager.notify(90, notification)
        ReminderScheduler.schedule(context, state)
    }
}
