package com.veltrix.aianalyst

import org.junit.Assert.assertEquals
import org.junit.Test

class HistoryDateLabelTest {
    @Test
    fun timestampNearUtcMidnightUsesWatCalendarDate() {
        assertEquals("Tuesday, 24 Nov 2026", historyDateLabel("2026-11-23T23:30:00Z"))
    }

    @Test
    fun timestampBeforeWatMidnightRemainsOnPreviousDate() {
        assertEquals("Monday, 23 Nov 2026", historyDateLabel("2026-11-23T22:59:59Z"))
    }

    @Test
    fun invalidTimestampUsesExplicitFallback() {
        assertEquals("Date unavailable", historyDateLabel("invalid"))
    }
}
