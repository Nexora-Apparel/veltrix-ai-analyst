package com.veltrix.aianalyst

import android.util.Log
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

data class FixturePrediction(
    val id: String,
    val fixtureId: String,
    val competition: String,
    val homeTeam: String,
    val awayTeam: String,
    val kickoffAt: String,
    val home: Double,
    val draw: Double,
    val away: Double,
    val bttsYes: Double,
    val bttsNo: Double,
    val over15: Double,
    val under15: Double,
    val over25: Double,
    val under25: Double,
    val over35: Double,
    val under35: Double,
    val researchOnly: Boolean = false,
)

data class PredictionFeedResult(
    val predictions: List<FixturePrediction>?,
    val error: String?,
)

data class PredictionHistoryEntry(
    val prediction: FixturePrediction,
    val generatedAt: String,
    val publishedAt: String,
    val publicationStatus: String,
    val settlementStatus: String,
    val homeGoals: Int?,
    val awayGoals: Int?,
    val settledAt: String?,
)

object PredictionApi {
    private const val TAG = "VeltrixPredictions"
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .callTimeout(20, TimeUnit.SECONDS)
        .build()

    suspend fun fetchUpcoming(): List<FixturePrediction>? = withContext(Dispatchers.IO) {
        val baseUrl = BuildConfig.API_BASE_URL.trim().trimEnd('/')
        if (baseUrl.isBlank()) {
            Log.w(TAG, "API base URL has not been configured")
            return@withContext null
        }

        val request = Request.Builder()
            .url("$baseUrl/v1/predictions")
            .get()
            .header("Accept", "application/json")
            .build()

        try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    Log.w(TAG, "Prediction API returned HTTP ${response.code}")
                    null
                } else {
                    val body = response.body?.string()
                        ?: throw IOException("Prediction API returned an empty response")
                    parsePredictions(body)
                }
            }
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: Exception) {
            Log.e(TAG, "Unable to load published predictions", exception)
            null
        }
    }

    suspend fun fetchResearchUpcoming(): PredictionFeedResult = withContext(Dispatchers.IO) {
        val baseUrl = BuildConfig.API_BASE_URL.trim().trimEnd('/')
        if (baseUrl.isBlank()) {
            val message = "API base URL is not configured"
            Log.w(TAG, message)
            return@withContext PredictionFeedResult(null, message)
        }

        try {
            val request = Request.Builder()
                .url("$baseUrl/v1/research/predictions")
                .get()
                .header("Accept", "application/json")
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val message = "HTTP ${response.code}"
                    Log.w(TAG, "Research feed request failed: $message")
                    PredictionFeedResult(null, message)
                } else {
                    val body = response.body?.string()
                        ?: throw IOException("Empty response body")
                    val predictions = parseResearchPredictions(body)
                    Log.i(TAG, "Research feed loaded: ${predictions.size} forecasts")
                    PredictionFeedResult(predictions, null)
                }
            }
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: Exception) {
            val detail = exception.message?.takeIf { it.isNotBlank() }
                ?: exception.javaClass.simpleName
            Log.e(TAG, "Research feed load failed: $detail", exception)
            PredictionFeedResult(null, detail)
        }
    }

    suspend fun fetchHistory(): List<PredictionHistoryEntry>? = withContext(Dispatchers.IO) {
        val baseUrl = BuildConfig.API_BASE_URL.trim().trimEnd('/')
        if (baseUrl.isBlank()) {
            Log.w(TAG, "API base URL has not been configured")
            return@withContext null
        }

        val request = Request.Builder()
            .url("$baseUrl/v1/predictions/history")
            .get()
            .header("Accept", "application/json")
            .build()

        try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    Log.w(TAG, "Prediction history API returned HTTP ${response.code}")
                    null
                } else {
                    val body = response.body?.string()
                        ?: throw IOException("Prediction history API returned an empty response")
                    parseHistory(body)
                }
            }
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: Exception) {
            Log.e(TAG, "Unable to load prediction history", exception)
            null
        }
    }

    internal fun parseResearchPredictions(json: String): List<FixturePrediction> {
        val root = JSONObject(json)
        require(root.optBoolean("research_only")) { "Research-only flag missing" }
        require(root.optString("publication_status") == "NOT_PUBLISHED") {
            "Research forecast must remain unpublished"
        }
        require(root.optString("production_promotion") == "LOCKED") {
            "Research forecast promotion must remain locked"
        }
        require(root.optString("value_betting") == "LOCKED") {
            "Research forecast value betting must remain locked"
        }
        return parsePredictions(json, researchOnly = true)
    }

    internal fun parsePredictions(
        json: String,
        researchOnly: Boolean = false,
    ): List<FixturePrediction> {
        val root = JSONObject(json)
        val items = root.optJSONArray("predictions")
            ?: throw IllegalArgumentException("Missing predictions array")
        return buildList(items.length()) {
            for (index in 0 until items.length()) {
                add(parsePrediction(items.getJSONObject(index), researchOnly))
            }
        }
    }

    internal fun parseHistory(json: String): List<PredictionHistoryEntry> {
        val root = JSONObject(json)
        val items = root.optJSONArray("predictions")
            ?: throw IllegalArgumentException("Missing predictions array")
        return buildList(items.length()) {
            for (index in 0 until items.length()) {
                val item = items.getJSONObject(index)
                val score = item.optJSONObject("final_score")
                add(
                    PredictionHistoryEntry(
                        prediction = parsePrediction(item),
                        generatedAt = item.getString("generated_at"),
                        publishedAt = item.getString("published_at"),
                        publicationStatus = item.getString("publication_status"),
                        settlementStatus = item.getString("settlement_status"),
                        homeGoals = score?.getInt("home_goals"),
                        awayGoals = score?.getInt("away_goals"),
                        settledAt = if (item.isNull("settled_at")) null
                            else item.getString("settled_at"),
                    )
                )
            }
        }
    }

    private fun parsePrediction(item: JSONObject, researchOnly: Boolean = false): FixturePrediction {
        val fixture = item.getJSONObject("fixture")
        val markets = item.getJSONObject("markets")
        val oneXTwo = markets.getJSONObject("one_x_two")
        val btts = markets.getJSONObject("btts")
        val over15 = markets.getJSONObject("over_under_1_5")
        val over25 = markets.getJSONObject("over_under_2_5")
        val over35 = markets.getJSONObject("over_under_3_5")

        return FixturePrediction(
            id = item.getString("prediction_id"),
            fixtureId = fixture.getString("fixture_id"),
            competition = fixture.getString("competition"),
            homeTeam = fixture.getString("home_team"),
            awayTeam = fixture.getString("away_team"),
            kickoffAt = fixture.getString("kickoff_at"),
            home = oneXTwo.getDouble("HOME"),
            draw = oneXTwo.getDouble("DRAW"),
            away = oneXTwo.getDouble("AWAY"),
            bttsYes = btts.getDouble("YES"),
            bttsNo = btts.getDouble("NO"),
            over15 = over15.getDouble("OVER"),
            under15 = over15.getDouble("UNDER"),
            over25 = over25.getDouble("OVER"),
            under25 = over25.getDouble("UNDER"),
            over35 = over35.getDouble("OVER"),
            under35 = over35.getDouble("UNDER"),
            researchOnly = researchOnly,
        )
    }
}
