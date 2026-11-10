package ru.sistema.player

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.util.AttributeSet
import android.view.View
import kotlin.math.cos
import kotlin.math.sin

class RuneView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    private val glow = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(40, 137, 255)
        style = Paint.Style.STROKE
        strokeWidth = 8f
    }
    private val line = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(117, 222, 255)
        style = Paint.Style.STROKE
        strokeWidth = 2.5f
    }
    private val core = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(85, 214, 255)
        style = Paint.Style.FILL
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val cx = width / 2f
        val cy = height / 2f
        val radius = width.coerceAtMost(height) * 0.34f
        canvas.drawCircle(cx, cy, radius * 1.18f, glow.apply { alpha = 40 })
        polygon(canvas, cx, cy, radius, 6, line)
        polygon(canvas, cx, cy, radius * 0.72f, 4, line)
        canvas.drawCircle(cx, cy, radius * 0.15f, core)
        canvas.drawLine(cx, cy - radius * 0.5f, cx, cy + radius * 0.5f, line)
    }

    private fun polygon(canvas: Canvas, cx: Float, cy: Float, radius: Float, sides: Int, paint: Paint) {
        val path = Path()
        for (index in 0 until sides) {
            val angle = Math.toRadians((-90 + index * 360.0 / sides))
            val x = cx + radius * cos(angle).toFloat()
            val y = cy + radius * sin(angle).toFloat()
            if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        path.close()
        canvas.drawPath(path, paint)
    }
}
