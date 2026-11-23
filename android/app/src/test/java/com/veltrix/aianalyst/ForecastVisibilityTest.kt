package com.veltrix.aianalyst

import java.time.Instant
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ForecastVisibilityTest {
    private val now = Instant.parse("2026-11-23T12:00:00Z")

    @Test
    fun futureKickoffKeepsForecastVisible() {
        assertTrue(forecastIsAvailable("2026-11-23T12:00:01Z", now))
    }

    @Test
    fun exactKickoffHidesForecast() {
        assertFalse(forecastIsAvailable("2026-11-23T12:00:00Z", now))
    }

    @Test
    fun pastKickoffHidesForecast() {
        assertFalse(forecastIsAvailable("2026-11-23T11:59:59Z", now))
    }

    @Test
    fun invalidKickoffHidesForecast() {
        assertFalse(forecastIsAvailable("not-a-timestamp", now))
    }
}
