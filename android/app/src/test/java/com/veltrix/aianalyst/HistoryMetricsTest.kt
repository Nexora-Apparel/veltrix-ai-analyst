package com.veltrix.aianalyst

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class HistoryMetricsTest {
    @Test
    fun highestProbabilityOutcomeIsSelected() {
        assertEquals("HOME", predictedOneXTwoOutcome(0.62, 0.23, 0.15))
        assertEquals("DRAW", predictedOneXTwoOutcome(0.20, 0.55, 0.25))
        assertEquals("AWAY", predictedOneXTwoOutcome(0.18, 0.22, 0.60))
    }

    @Test
    fun tiedMaximumDoesNotInventAPick() {
        assertNull(predictedOneXTwoOutcome(0.40, 0.20, 0.40))
    }

    @Test
    fun settledCorrectAndIncorrectResultsAreScored() {
        assertTrue(settledOneXTwoCorrect(0.62, 0.23, 0.15, 2, 1, "SETTLED")!!)
        assertFalse(settledOneXTwoCorrect(0.62, 0.23, 0.15, 0, 2, "SETTLED")!!)
        assertTrue(settledOneXTwoCorrect(0.20, 0.55, 0.25, 1, 1, "SETTLED")!!)
    }

    @Test
    fun pendingOrMissingScoresAreNotScored() {
        assertNull(settledOneXTwoCorrect(0.62, 0.23, 0.15, 2, 1, "PENDING"))
        assertNull(settledOneXTwoCorrect(0.62, 0.23, 0.15, null, 1, "SETTLED"))
    }
}
