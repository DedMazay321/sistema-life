package ru.sistema.player

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import java.time.LocalDate

class ProgressWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        val state = PlayerStore(context).load(); val today = LocalDate.now()
        val done = GameEngine.completedToday(state, today).size
        val progress = GameEngine.levelProgress(state.totalXp)
        ids.forEach { id ->
            val views = RemoteViews(context.packageName, R.layout.sistema_widget)
            views.setTextViewText(R.id.widget_title, "СИСТЕМА  ·  РАНГ ${progress.rank}")
            views.setTextViewText(R.id.widget_progress, "$done / 6")
            views.setTextViewText(R.id.widget_level, "Уровень ${progress.level}  ·  ${state.totalXp} XP")
            views.setTextViewText(R.id.widget_hint, if (done == 6) "Протокол завершён" else "Открыть ежедневные задания")
            val open = PendingIntent.getActivity(context, 92, Intent(context, MainActivity::class.java), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            views.setOnClickPendingIntent(R.id.widget_root, open)
            manager.updateAppWidget(id, views)
        }
    }

    companion object {
        fun refresh(context: Context) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(ComponentName(context, ProgressWidgetProvider::class.java))
            if (ids.isNotEmpty()) ProgressWidgetProvider().onUpdate(context, manager, ids)
        }
    }
}
