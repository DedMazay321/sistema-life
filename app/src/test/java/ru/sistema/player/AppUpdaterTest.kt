package ru.sistema.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AppUpdaterTest {
    @Test fun `selects newest stable Android release with APK`() {
        val update = AppUpdater.selectUpdate(releases, 3)
        assertEquals(5, update?.versionCode)
        assertEquals("5.0", update?.versionName)
        assertEquals("https://github.com/DedMazay321/sistema-life/releases/download/android-v5/Sistema.apk", update?.apkUrl)
    }

    @Test fun `does not downgrade or select web releases`() {
        assertNull(AppUpdater.selectUpdate(releases, 5))
    }

    @Test fun `rejects non HTTPS assets`() {
        val raw = """[{"tag_name":"android-v6","name":"Система 6.0","html_url":"https://github.com/release","assets":[{"name":"Sistema.apk","browser_download_url":"http://unsafe/Sistema.apk"}]}]"""
        assertNull(AppUpdater.selectUpdate(raw, 3))
    }

    private val releases = """
        [
          {"tag_name":"web-v4.0","name":"Web 4.0","assets":[]},
          {"tag_name":"android-v5","name":"Система 5.0","body":"Новые задания","html_url":"https://github.com/releases/android-v5","assets":[{"name":"Sistema.apk","browser_download_url":"https://github.com/DedMazay321/sistema-life/releases/download/android-v5/Sistema.apk"}]},
          {"tag_name":"android-v6","name":"Система 6.0","draft":true,"html_url":"https://github.com/releases/android-v6","assets":[{"name":"Sistema.apk","browser_download_url":"https://github.com/Sistema.apk"}]},
          {"tag_name":"android-v4","name":"Система 4.0","html_url":"https://github.com/releases/android-v4","assets":[{"name":"Sistema.apk","browser_download_url":"https://github.com/DedMazay321/sistema-life/releases/download/android-v4/Sistema.apk"}]}
        ]
    """.trimIndent()
}
