package com.veltrix.aianalyst

internal fun predictedOneXTwoOutcome(home: Double, draw: Double, away: Double): String? {
    val outcomes = listOf("HOME" to home, "DRAW" to draw, "AWAY" to away)
    val maximum = outcomes.maxOf { it.second }
    val leaders = outcomes.filter { kotlin.math.abs(it.second - maximum) < 1e-9 }
    return leaders.singleOrNull()?.first
}

internal fun settledOneXTwoCorrect(
    homeProbability: Double,
    drawProbability: Double,
    awayProbability: Double,
    homeGoals: Int?,
    awayGoals: Int?,
    settlementStatus: String,
): Boolean? {
    if (settlementStatus != "SETTLED" || homeGoals == null || awayGoals == null) return null
    val predicted = predictedOneXTwoOutcome(homeProbability, drawProbability, awayProbability)
        ?: return null
    val actual = when {
        homeGoals > awayGoals -> "HOME"
        homeGoals < awayGoals -> "AWAY"
        else -> "DRAW"
    }
    return predicted == actual
}
