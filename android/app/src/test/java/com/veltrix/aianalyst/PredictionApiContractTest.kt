package com.veltrix.aianalyst

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class PredictionApiContractTest {
    private fun feed(
        researchOnly: Boolean = true,
        publicationStatus: String = "NOT_PUBLISHED",
        productionPromotion: String = "LOCKED",
        valueBetting: String = "LOCKED",
    ) = """
        {
          "research_only": $researchOnly,
          "publication_status": "$publicationStatus",
          "production_promotion": "$productionPromotion",
          "value_betting": "$valueBetting",
          "predictions": [{
            "prediction_id": "research-1",
            "fixture": {
              "fixture_id": "fixture-1",
              "competition": "Test League",
              "home_team": "Home FC",
              "away_team": "Away FC",
              "kickoff_at": "2026-11-24T18:00:00Z"
            },
            "markets": {
              "one_x_two": {"HOME": 0.45, "DRAW": 0.28, "AWAY": 0.27},
              "btts": {"YES": 0.51, "NO": 0.49},
              "over_under_1_5": {"OVER": 0.72, "UNDER": 0.28},
              "over_under_2_5": {"OVER": 0.50, "UNDER": 0.50},
              "over_under_3_5": {"OVER": 0.29, "UNDER": 0.71}
            }
          }]
        }
    """.trimIndent()

    @Test
    fun validResearchFeedIsMarkedResearchOnly() {
        val parsed = PredictionApi.parseResearchPredictions(feed())
        assertEquals(1, parsed.size)
        assertTrue(parsed.single().researchOnly)
        assertEquals("Home FC", parsed.single().homeTeam)
    }

    @Test
    fun publishedPayloadCannotEnterResearchParser() {
        assertThrows(IllegalArgumentException::class.java) {
            PredictionApi.parseResearchPredictions(
                feed(researchOnly = false, publicationStatus = "PUBLISHED")
            )
        }
    }

    @Test
    fun unlockedPromotionIsRejected() {
        assertThrows(IllegalArgumentException::class.java) {
            PredictionApi.parseResearchPredictions(feed(productionPromotion = "UNLOCKED"))
        }
    }

    @Test
    fun unlockedValueBettingIsRejected() {
        assertThrows(IllegalArgumentException::class.java) {
            PredictionApi.parseResearchPredictions(feed(valueBetting = "UNLOCKED"))
        }
    }

    @Test
    fun ordinaryPublishedParserDoesNotMarkPredictionsAsResearch() {
        val parsed = PredictionApi.parsePredictions(feed())
        assertFalse(parsed.single().researchOnly)
    }
}
