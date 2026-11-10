package ru.sistema.player

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.content.pm.Signature
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.core.content.FileProvider
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

data class AppUpdate(
    val versionCode: Int,
    val versionName: String,
    val apkUrl: String,
    val pageUrl: String,
    val notes: String,
)

class AppUpdater(private val activity: Activity) {
    private val preferences = activity.getSharedPreferences("app_updates", Context.MODE_PRIVATE)
    private var checking = false
    private var downloading = false
    @Volatile private var cancelled = false
    private var pendingInstall: File? = null

    fun check(manual: Boolean) {
        if (checking || downloading) {
            if (manual) toast("Проверка или загрузка уже выполняется")
            return
        }
        val now = System.currentTimeMillis()
        if (!manual && now - preferences.getLong("last_check", 0L) < AUTO_CHECK_INTERVAL) return
        checking = true
        val waiting = if (manual) AlertDialog.Builder(activity)
            .setTitle("ОБНОВЛЕНИЕ СИСТЕМЫ").setMessage("Проверяем GitHub Releases…")
            .setCancelable(false).show() else null
        Thread {
            try {
                val response = get(RELEASES_URL)
                val update = selectUpdate(response, currentVersionCode())
                preferences.edit().putLong("last_check", now).apply()
                onUi {
                    checking = false
                    waiting?.dismiss()
                    if (update == null) {
                        if (manual) toast("Установлена последняя версия")
                    } else showUpdate(update)
                }
            } catch (_: Exception) {
                onUi {
                    checking = false
                    waiting?.dismiss()
                    if (manual) toast("Не удалось проверить обновление. Проверь интернет.")
                }
            }
        }.start()
    }

    fun onResume() {
        val file = pendingInstall ?: return
        if (Build.VERSION.SDK_INT < 26 || activity.packageManager.canRequestPackageInstalls()) {
            pendingInstall = null
            launchInstaller(file)
        }
    }

    private fun showUpdate(update: AppUpdate) {
        val description = buildString {
            append("Доступна версия ${update.versionName}\n\n")
            append(update.notes.ifBlank { "Новая версия готова к установке." })
            append("\n\nПрогресс сохранится. Android попросит подтвердить установку.")
        }
        AlertDialog.Builder(activity).setTitle("НОВАЯ ВЕРСИЯ СИСТЕМЫ").setMessage(description)
            .setPositiveButton("ОБНОВИТЬ") { _, _ -> download(update) }
            .setNeutralButton("GITHUB") { _, _ -> openRelease(update.pageUrl) }
            .setNegativeButton("ПОЗЖЕ", null).show()
    }

    private fun download(update: AppUpdate) {
        if (downloading) return
        downloading = true
        cancelled = false
        val density = activity.resources.displayMetrics.density
        val padding = (20 * density).toInt()
        val container = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding / 2, padding, 0)
        }
        val status = TextView(activity).apply {
            text = "Подключение к GitHub…"
            setTextColor(Color.rgb(242, 247, 252))
            textSize = 13f
            gravity = Gravity.CENTER
        }
        val progress = ProgressBar(activity, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            isIndeterminate = true
        }
        container.addView(status)
        container.addView(progress, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, (8 * density).toInt()).apply {
            topMargin = padding / 2
        })
        val dialog = AlertDialog.Builder(activity).setTitle("ЗАГРУЗКА ВЕРСИИ ${update.versionName}")
            .setView(container).setCancelable(false)
            .setNegativeButton("ОТМЕНА") { _, _ -> cancelled = true }.show()
        val directory = File(activity.cacheDir, "updates")
        val partial = File(directory, "Sistema-${update.versionCode}.part")
        val target = File(directory, "Sistema-${update.versionCode}.apk")
        Thread {
            try {
                directory.mkdirs()
                partial.delete()
                target.delete()
                downloadFile(update.apkUrl, partial) { percent, downloaded, total ->
                    onUi {
                        progress.isIndeterminate = percent == null
                        if (percent != null) progress.progress = percent
                        status.text = if (total > 0) "${percent ?: 0}%  ·  ${downloaded / 1024} / ${total / 1024} КБ"
                        else "${downloaded / 1024} КБ загружено"
                    }
                }
                if (!partial.renameTo(target)) {
                    partial.copyTo(target, overwrite = true)
                    partial.delete()
                }
                validateApk(target)
                onUi {
                    downloading = false
                    dialog.dismiss()
                    install(target)
                }
            } catch (_: Exception) {
                partial.delete()
                onUi {
                    downloading = false
                    dialog.dismiss()
                    if (!cancelled) AlertDialog.Builder(activity).setTitle("ЗАГРУЗКА НЕ ЗАВЕРШЕНА")
                        .setMessage("Не удалось скачать или проверить APK. Попробуй ещё раз или открой релиз в браузере.")
                        .setPositiveButton("ПОВТОРИТЬ") { _, _ -> download(update) }
                        .setNeutralButton("GITHUB") { _, _ -> openRelease(update.pageUrl) }
                        .setNegativeButton("ЗАКРЫТЬ", null).show()
                }
            }
        }.start()
    }

    private fun install(file: File) {
        if (Build.VERSION.SDK_INT >= 26 && !activity.packageManager.canRequestPackageInstalls()) {
            pendingInstall = file
            AlertDialog.Builder(activity).setTitle("РАЗРЕШИ УСТАНОВКУ")
                .setMessage("Открой настройку «Установка неизвестных приложений» для Системы, затем вернись — установка продолжится.")
                .setPositiveButton("ОТКРЫТЬ НАСТРОЙКИ") { _, _ ->
                    activity.startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${activity.packageName}")))
                }.setNegativeButton("ПОЗЖЕ", null).show()
            return
        }
        launchInstaller(file)
    }

    private fun launchInstaller(file: File) {
        try {
            val uri = FileProvider.getUriForFile(activity, "${activity.packageName}.updater", file)
            activity.startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uri, APK_MIME)
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK))
        } catch (_: Exception) {
            toast("Не удалось открыть установщик Android")
        }
    }

    private fun validateApk(file: File) {
        val info = packageInfoForArchive(file)
            ?: throw IOException("APK не распознан")
        if (info.packageName != activity.packageName) throw IOException("Неверный пакет")
        val code = if (Build.VERSION.SDK_INT >= 28) info.longVersionCode else info.versionCode.toLong()
        if (code <= currentVersionCode()) throw IOException("Устаревшая версия")
        val installed = packageInfoForInstalledApp()
        if (signingCertificates(info) != signingCertificates(installed)) {
            throw IOException("Подпись APK не совпадает с установленной версией")
        }
    }

    @Suppress("DEPRECATION")
    private fun packageInfoForArchive(file: File): PackageInfo? = activity.packageManager.getPackageArchiveInfo(
        file.absolutePath,
        if (Build.VERSION.SDK_INT >= 28) PackageManager.GET_SIGNING_CERTIFICATES else PackageManager.GET_SIGNATURES,
    )

    @Suppress("DEPRECATION")
    private fun packageInfoForInstalledApp(): PackageInfo = activity.packageManager.getPackageInfo(
        activity.packageName,
        if (Build.VERSION.SDK_INT >= 28) PackageManager.GET_SIGNING_CERTIFICATES else PackageManager.GET_SIGNATURES,
    )

    @Suppress("DEPRECATION")
    private fun signingCertificates(info: PackageInfo): Set<String> {
        val signatures: Array<Signature> = if (Build.VERSION.SDK_INT >= 28) {
            info.signingInfo?.apkContentsSigners ?: emptyArray()
        } else {
            info.signatures ?: emptyArray()
        }
        if (signatures.isEmpty()) throw IOException("У APK отсутствует подпись")
        return signatures.mapTo(mutableSetOf()) { signature ->
            java.security.MessageDigest.getInstance("SHA-256")
                .digest(signature.toByteArray())
                .joinToString("") { byte -> "%02x".format(byte) }
        }
    }

    private fun currentVersionCode(): Int {
        val info = activity.packageManager.getPackageInfo(activity.packageName, 0)
        return if (Build.VERSION.SDK_INT >= 28) info.longVersionCode.toInt() else info.versionCode
    }

    private fun openRelease(url: String) {
        runCatching { activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
            .onFailure { toast("Не удалось открыть GitHub") }
    }

    private fun onUi(action: () -> Unit) = activity.runOnUiThread {
        if (!activity.isFinishing && !activity.isDestroyed) action()
    }

    private fun toast(message: String) = Toast.makeText(activity, message, Toast.LENGTH_LONG).show()

    companion object {
        private const val RELEASES_URL = "https://api.github.com/repos/DedMazay321/sistema-life/releases?per_page=30"
        private const val APK_MIME = "application/vnd.android.package-archive"
        private const val AUTO_CHECK_INTERVAL = 6 * 60 * 60 * 1000L

        fun selectUpdate(raw: String, currentVersionCode: Int): AppUpdate? {
            val releases = JSONArray(raw)
            val candidates = mutableListOf<AppUpdate>()
            for (index in 0 until releases.length()) {
                val release = releases.optJSONObject(index) ?: continue
                if (release.optBoolean("draft") || release.optBoolean("prerelease")) continue
                val tag = release.optString("tag_name")
                if (!tag.startsWith("android-v")) continue
                val code = tag.removePrefix("android-v").toIntOrNull() ?: continue
                if (code <= currentVersionCode) continue
                val assets = release.optJSONArray("assets") ?: continue
                var apk: JSONObject? = null
                for (assetIndex in 0 until assets.length()) {
                    val asset = assets.optJSONObject(assetIndex) ?: continue
                    if (asset.optString("name").endsWith(".apk", ignoreCase = true)) {
                        apk = asset
                        break
                    }
                }
                val apkUrl = apk?.optString("browser_download_url").orEmpty()
                val pageUrl = release.optString("html_url")
                if (!apkUrl.startsWith("https://") || !pageUrl.startsWith("https://")) continue
                val title = release.optString("name")
                val versionName = Regex("\\d+(?:\\.\\d+)+").find(title)?.value ?: "сборка $code"
                candidates += AppUpdate(code, versionName, apkUrl, pageUrl, release.optString("body").trim().take(3500))
            }
            return candidates.maxByOrNull { it.versionCode }
        }

        private fun get(url: String): String {
            val connection = (URL(url).openConnection() as HttpURLConnection).apply {
                connectTimeout = 10000
                readTimeout = 15000
                setRequestProperty("Accept", "application/vnd.github+json")
                setRequestProperty("User-Agent", "Sistema-Android")
            }
            return try {
                if (connection.responseCode !in 200..299) throw IOException("HTTP ${connection.responseCode}")
                connection.inputStream.bufferedReader().use { it.readText() }
            } finally {
                connection.disconnect()
            }
        }

        private fun AppUpdater.downloadFile(url: String, destination: File, progress: (Int?, Long, Long) -> Unit) {
            val connection = (URL(url).openConnection() as HttpURLConnection).apply {
                connectTimeout = 15000
                readTimeout = 30000
                instanceFollowRedirects = true
                setRequestProperty("User-Agent", "Sistema-Android")
            }
            try {
                if (connection.responseCode !in 200..299) throw IOException("HTTP ${connection.responseCode}")
                val total = connection.contentLengthLong.coerceAtLeast(0L)
                var downloaded = 0L
                connection.inputStream.use { input ->
                    FileOutputStream(destination).use { output ->
                        val buffer = ByteArray(32 * 1024)
                        while (true) {
                            val count = input.read(buffer)
                            if (count < 0) break
                            if (cancelled) throw IOException("Отменено")
                            output.write(buffer, 0, count)
                            downloaded += count
                            val percent = if (total > 0) (downloaded * 100 / total).toInt().coerceIn(0, 100) else null
                            progress(percent, downloaded, total)
                        }
                    }
                }
                if (total > 0 && downloaded != total) throw IOException("Неполный файл")
                if (downloaded == 0L) throw IOException("Пустой файл")
            } finally {
                connection.disconnect()
            }
        }
    }
}
