package com.veltrix.aianalyst

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.roundToInt

private class Pal(
    val bg: Color, val card: Color, val text: Color, val sub: Color,
    val line: Color, val fill: Color, val bar: Color,
    val blue: Color, val green: Color, val orange: Color, val red: Color,
)

private val LightPal = Pal(
    Color(0xFFF2F2F7), Color.White, Color.Black, Color(0xFF8E8E93),
    Color(0x2E3C3C43), Color(0x1F787880), Color(0xEBFFFFFF),
    Color(0xFF007AFF), Color(0xFF34C759), Color(0xFFFF9500), Color(0xFFFF3B30),
)
private val DarkPal = Pal(
    Color.Black, Color(0xFF1C1C1E), Color.White, Color(0xFF98989F),
    Color(0x99545458), Color(0x3D787880), Color(0xEB1C1C1E),
    Color(0xFF0A84FF), Color(0xFF30D158), Color(0xFFFF9F0A), Color(0xFFFF453A),
)

private val LocalPal = compositionLocalOf { LightPal }
private val Font = FontFamily.SansSerif

private fun t(size: Int, w: FontWeight = FontWeight.Normal, c: Color) =
    TextStyle(fontFamily = Font, fontSize = size.sp, fontWeight = w, color = c)

private enum class Tab(val label: String, val icon: ImageVector) {
    Home("Home", Icons.Filled.Home),
    History("History", Icons.Filled.History),
    Btts("BTTS", Icons.Filled.CheckCircle),
    Value("Value Bet", Icons.Filled.TrendingUp),
    OverUnder("Over/Under", Icons.Filled.BarChart),
    Menu("Menu", Icons.Filled.Menu),
}

@Composable
fun VeltrixDashboard() {
    val pal = if (isSystemInDarkTheme()) DarkPal else LightPal
    var tab by remember { mutableStateOf(Tab.Home) }
    var predictions by remember { mutableStateOf<List<FixturePrediction>?>(null) }
    var researchPredictions by remember { mutableStateOf<List<FixturePrediction>?>(null) }
    var researchError by remember { mutableStateOf<String?>(null) }
    var history by remember { mutableStateOf<List<PredictionHistoryEntry>?>(null) }
    var loading by remember { mutableStateOf(true) }
    var refreshToken by remember { mutableIntStateOf(0) }

    LaunchedEffect(refreshToken) {
        loading = true
        predictions = PredictionApi.fetchUpcoming()
        val researchFeed = PredictionApi.fetchResearchUpcoming()
        researchPredictions = researchFeed.predictions
        researchError = researchFeed.error
        history = PredictionApi.fetchHistory()
        loading = false
    }

    CompositionLocalProvider(LocalPal provides pal) {
        Box(Modifier.fillMaxSize().background(pal.bg)) {
            when (tab) {
                Tab.Home -> HomeScreen(predictions, researchPredictions, researchError, loading) { refreshToken++ }
                Tab.History -> HistoryScreen(history, loading)
                Tab.Btts -> BttsScreen(predictions, researchPredictions, researchError, loading)
                Tab.Value -> ValueScreen()
                Tab.OverUnder -> OverUnderScreen(predictions, researchPredictions, researchError, loading)
                Tab.Menu -> MenuScreen()
            }
            BottomMenu(tab, { tab = it }, Modifier.align(Alignment.BottomCenter))
        }
    }
}

@Composable
private fun BottomMenu(selected: Tab, onSelect: (Tab) -> Unit, modifier: Modifier) {
    val p = LocalPal.current
    val shape = RoundedCornerShape(26.dp)
    Row(
        modifier
            .navigationBarsPadding()
            .padding(horizontal = 10.dp, vertical = 10.dp)
            .shadow(14.dp, shape)
            .clip(shape)
            .background(p.bar)
            .border(0.5.dp, p.line, shape)
            .padding(horizontal = 4.dp, vertical = 6.dp),
    ) {
        Tab.values().forEach { item ->
            val on = item == selected
            Column(
                Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(18.dp))
                    .background(if (on) p.blue.copy(alpha = 0.12f) else Color.Transparent)
                    .clickable { onSelect(item) }
                    .padding(vertical = 6.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(3.dp),
            ) {
                Icon(item.icon, item.label, Modifier.size(24.dp), tint = if (on) p.blue else p.sub)
                Text(item.label, style = t(10, FontWeight.Medium, if (on) p.blue else p.sub), maxLines = 1)
            }
        }
    }
}

@Composable
private fun Screen(
    title: String,
    subtitle: String,
    content: @Composable ColumnScope.() -> Unit,
) {
    val p = LocalPal.current
    LazyColumn(
        Modifier.fillMaxSize().statusBarsPadding(),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 120.dp),
    ) {
        item {
            Column {
                Text(title, style = t(34, FontWeight.Bold, p.text))
                Text(
                    subtitle,
                    style = t(15, c = p.sub),
                    modifier = Modifier.padding(top = 2.dp, bottom = 14.dp),
                )
                Column(content = content)
            }
        }
    }
}

@Composable
private fun Card(content: @Composable ColumnScope.() -> Unit) {
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(LocalPal.current.card),
        content = content,
    )
}

@Composable
private fun Divider() =
    Box(Modifier.fillMaxWidth().height(0.5.dp).background(LocalPal.current.line))

@Composable
private fun SectionTitle(text: String) =
    Text(
        text,
        style = t(22, FontWeight.Bold, LocalPal.current.text),
        modifier = Modifier.padding(start = 4.dp, top = 22.dp, bottom = 8.dp),
    )

@Composable
private fun Pill(text: String, color: Color) {
    Text(
        text,
        style = t(13, FontWeight.SemiBold, color),
        modifier = Modifier
            .clip(CircleShape)
            .background(color.copy(alpha = 0.16f))
            .padding(horizontal = 10.dp, vertical = 4.dp),
    )
}

@Composable
private fun SplitBar(parts: List<Pair<Int, Color>>) {
    Row(
        Modifier.fillMaxWidth()
            .padding(top = 12.dp, bottom = 6.dp)
            .height(8.dp)
            .clip(RoundedCornerShape(4.dp)),
        horizontalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        parts.forEach { (weight, color) ->
            Box(
                Modifier.weight(weight.coerceAtLeast(1).toFloat())
                    .fillMaxHeight()
                    .background(color),
            )
        }
    }
}

@Composable
private fun Legend(items: List<Pair<String, String>>) {
    val p = LocalPal.current
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        items.forEach { (label, value) ->
            Row {
                Text("$label ", style = t(13, c = p.sub))
                Text(value, style = t(13, FontWeight.SemiBold, p.text))
            }
        }
    }
}

@Composable
private fun MatchHeader(
    teams: String,
    meta: String,
    trailing: @Composable () -> Unit,
) {
    val p = LocalPal.current
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(teams, style = t(17, FontWeight.SemiBold, p.text))
            Text(meta, style = t(13, c = p.sub), modifier = Modifier.padding(top = 2.dp))
        }
        trailing()
    }
}

@Composable
private fun Ring(percent: Int, color: Color, size: Dp = 54.dp) {
    val p = LocalPal.current
    Box(Modifier.size(size), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize()) {
            val stroke = 6.dp.toPx()
            val arcSize = Size(this.size.width - stroke, this.size.height - stroke)
            val topLeft = Offset(stroke / 2, stroke / 2)
            drawArc(p.fill, 0f, 360f, false, topLeft, arcSize, style = Stroke(stroke))
            drawArc(
                color, -90f, percent.coerceIn(0, 100) * 3.6f, false,
                topLeft, arcSize, style = Stroke(stroke, cap = StrokeCap.Round),
            )
        }
        Text("$percent%", style = t(14, FontWeight.Bold, p.text))
    }
}

@Composable
private fun EmptyState(message: String) {
    Text(
        message,
        style = t(14, c = LocalPal.current.sub),
        modifier = Modifier.fillMaxWidth().padding(vertical = 24.dp),
    )
}

@Composable
private fun ResearchFeedWarning(error: String?) {
    if (error != null) {
        Text(
            "Research feed unavailable · $error",
            style = t(12, FontWeight.Medium, LocalPal.current.orange),
            modifier = Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 6.dp),
        )
    }
}

@Composable
private fun HomeScreen(
    predictions: List<FixturePrediction>?,
    researchPredictions: List<FixturePrediction>?,
    researchError: String?,
    loading: Boolean,
    onRefresh: () -> Unit,
) {
    val p = LocalPal.current
    val matches = mergePredictions(predictions, researchPredictions)
    Screen("Veltrix", "Published and research-only match analysis") {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SectionTitle("Upcoming predictions")
            Row(
                Modifier.clip(CircleShape).clickable(onClick = onRefresh).padding(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Filled.Refresh, "Refresh predictions", tint = p.blue, modifier = Modifier.size(19.dp))
                Text("Refresh", style = t(13, FontWeight.Medium, p.blue))
            }
        }

        ResearchFeedWarning(researchError)
        when {
            loading && predictions == null && researchPredictions == null -> EmptyState("Loading predictions…")
            predictions == null && researchPredictions == null -> EmptyState("Predictions are temporarily unavailable.")
            matches.isEmpty() -> EmptyState("No upcoming predictions.")
            else -> Card {
                matches.forEachIndexed { index, match ->
                    if (index > 0) Divider()
                    Column(Modifier.padding(16.dp)) {
                        MatchHeader(
                            "${match.homeTeam} vs ${match.awayTeam}",
                            matchMeta(match),
                        ) {
                            Pill(
                                if (match.researchOnly) "RESEARCH ONLY" else "1X2",
                                if (match.researchOnly) p.orange else p.blue,
                            )
                        }
                        SplitBar(
                            listOf(
                                percent(match.home) to p.blue,
                                percent(match.draw) to p.sub,
                                percent(match.away) to p.orange,
                            ),
                        )
                        Legend(
                            listOf(
                                "1" to "${percent(match.home)}%",
                                "X" to "${percent(match.draw)}%",
                                "2" to "${percent(match.away)}%",
                            ),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun HistoryScreen(
    history: List<PredictionHistoryEntry>?,
    loading: Boolean,
) {
    val p = LocalPal.current
    val entries = history.orEmpty()
    Screen("History", "Published predictions and verified results") {
        when {
            loading && history == null -> EmptyState("Loading prediction history…")
            history == null -> EmptyState("Prediction history is temporarily unavailable.")
            entries.isEmpty() -> EmptyState("No previously published predictions yet.")
            else -> Card {
                entries.forEachIndexed { index, entry ->
                    if (index > 0) Divider()
                    val match = entry.prediction
                    Column(Modifier.padding(16.dp)) {
                        MatchHeader(
                            "${match.homeTeam} vs ${match.awayTeam}",
                            "${match.competition} · ${formatHistoryKickoff(match.kickoffAt)}",
                        ) {
                            Pill(
                                if (entry.settlementStatus == "SETTLED") "SETTLED"
                                else "AWAITING RESULT",
                                if (entry.settlementStatus == "SETTLED") p.green else p.orange,
                            )
                        }
                        if (entry.settlementStatus == "SETTLED") {
                            Text(
                                "Full time  ${entry.homeGoals} - ${entry.awayGoals}",
                                style = t(18, FontWeight.Bold, p.text),
                                modifier = Modifier.padding(top = 12.dp),
                            )
                            val actualOutcome = when {
                                (entry.homeGoals ?: 0) > (entry.awayGoals ?: 0) -> "HOME"
                                (entry.homeGoals ?: 0) < (entry.awayGoals ?: 0) -> "AWAY"
                                else -> "DRAW"
                            }
                            Text(
                                "Final 1X2 result: $actualOutcome",
                                style = t(13, c = p.sub),
                                modifier = Modifier.padding(top = 3.dp),
                            )
                        } else {
                            Text(
                                "Final score is awaiting verified source evidence.",
                                style = t(13, c = p.sub),
                                modifier = Modifier.padding(top = 12.dp),
                            )
                        }
                        Text(
                            "1X2  ·  H ${percent(match.home)}%   D ${percent(match.draw)}%   A ${percent(match.away)}%",
                            style = t(13, FontWeight.Medium, p.text),
                            modifier = Modifier.padding(top = 10.dp),
                        )
                        if (entry.publicationStatus == "WITHDRAWN") {
                            Text(
                                "Withdrawn before kickoff",
                                style = t(12, FontWeight.Medium, p.orange),
                                modifier = Modifier.padding(top = 4.dp),
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun BttsScreen(
    predictions: List<FixturePrediction>?,
    researchPredictions: List<FixturePrediction>?,
    researchError: String?,
    loading: Boolean,
) {
    val p = LocalPal.current
    val matches = mergePredictions(predictions, researchPredictions)
    Screen("BTTS", "Both teams to score") {
        ResearchFeedWarning(researchError)
        when {
            loading && predictions == null && researchPredictions == null -> EmptyState("Loading predictions…")
            predictions == null && researchPredictions == null -> EmptyState("Predictions are temporarily unavailable.")
            matches.isEmpty() -> EmptyState("No upcoming predictions.")
            else -> Card {
                matches.sortedByDescending { it.bttsYes }.forEachIndexed { index, match ->
                    if (index > 0) Divider()
                    Column(Modifier.padding(16.dp)) {
                        MatchHeader(
                            "${match.homeTeam} vs ${match.awayTeam}",
                            "${match.competition} · ${formatKickoff(match.kickoffAt)}",
                        ) {
                            Ring(
                                percent(match.bttsYes),
                                if (match.bttsYes >= 0.6) p.green else p.orange,
                            )
                        }
                        SplitBar(
                            listOf(
                                percent(match.bttsYes) to p.green,
                                percent(match.bttsNo) to p.red,
                            ),
                        )
                        Legend(
                            listOf(
                                "Yes" to "${percent(match.bttsYes)}%",
                                "No" to "${percent(match.bttsNo)}%",
                            ),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ValueScreen() {
    Screen("Value Bets", "Value selections") {
        Card {
            EmptyState("Value betting is locked until the model passes independent validation.")
        }
    }
}

@Composable
private fun OverUnderScreen(
    predictions: List<FixturePrediction>?,
    researchPredictions: List<FixturePrediction>?,
    researchError: String?,
    loading: Boolean,
) {
    val p = LocalPal.current
    val matches = mergePredictions(predictions, researchPredictions)
    var line by remember { mutableStateOf("2.5") }
    Screen("Over / Under", "Total goals") {
        Row(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(9.dp)).background(p.fill).padding(2.dp),
        ) {
            listOf("1.5", "2.5", "3.5").forEach { selectedLine ->
                val selected = selectedLine == line
                Box(
                    Modifier.weight(1f)
                        .clip(RoundedCornerShape(7.dp))
                        .background(if (selected) p.card else Color.Transparent)
                        .clickable { line = selectedLine }
                        .padding(vertical = 7.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(selectedLine, style = t(13, FontWeight.SemiBold, p.text))
                }
            }
        }
        Spacer(Modifier.height(14.dp))
        ResearchFeedWarning(researchError)

        when {
            loading && predictions == null && researchPredictions == null -> EmptyState("Loading predictions…")
            predictions == null && researchPredictions == null -> EmptyState("Predictions are temporarily unavailable.")
            matches.isEmpty() -> EmptyState("No upcoming predictions.")
            else -> Card {
                matches.forEachIndexed { index, match ->
                    if (index > 0) Divider()
                    val over = when (line) {
                        "1.5" -> match.over15
                        "3.5" -> match.over35
                        else -> match.over25
                    }
                    val under = when (line) {
                        "1.5" -> match.under15
                        "3.5" -> match.under35
                        else -> match.under25
                    }
                    Column(Modifier.padding(16.dp)) {
                        MatchHeader(
                            "${match.homeTeam} vs ${match.awayTeam}",
                            "${match.competition} · ${formatKickoff(match.kickoffAt)}",
                        ) {
                            Pill(
                                if (over >= 0.5) "Over $line" else "Under $line",
                                if (over >= 0.5) p.green else p.orange,
                            )
                        }
                        SplitBar(listOf(percent(over) to p.green, percent(under) to p.red))
                        Legend(listOf("Over" to "${percent(over)}%", "Under" to "${percent(under)}%"))
                    }
                }
            }
        }
    }
}

@Composable
private fun MenuScreen() {
    Screen("Menu", "Veltrix AI Analyst") {
        SectionTitle("Preferences")
        Card {
            InfoRow("Odds format", "Decimal")
            Divider()
            InfoRow("App version", "0.1.0")
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    val p = LocalPal.current
    Row(
        Modifier.fillMaxWidth().padding(16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = t(17, c = p.text))
        Text(value, style = t(17, c = p.sub))
    }
}

private fun mergePredictions(
    published: List<FixturePrediction>?,
    research: List<FixturePrediction>?,
): List<FixturePrediction> {
    val publishedPredictions = published.orEmpty()
    val publishedFixtureIds = publishedPredictions.map { it.fixtureId }.toSet()
    return publishedPredictions + research.orEmpty().filterNot {
        it.fixtureId in publishedFixtureIds
    }
}

private fun matchMeta(match: FixturePrediction): String {
    val kickoff = "${match.competition} · ${formatKickoff(match.kickoffAt)}"
    return if (match.researchOnly) "$kickoff · RESEARCH ONLY" else kickoff
}

private fun percent(value: Double): Int = (value * 100.0).roundToInt().coerceIn(0, 100)

private fun formatHistoryKickoff(value: String): String = runCatching {
    DateTimeFormatter.ofPattern("dd MMM yyyy · HH:mm", Locale.getDefault())
        .withZone(ZoneId.systemDefault())
        .format(Instant.parse(value))
}.getOrDefault(value)

private fun formatKickoff(value: String): String = runCatching {
    DateTimeFormatter.ofPattern("HH:mm", Locale.getDefault())
        .withZone(ZoneId.systemDefault())
        .format(Instant.parse(value))
}.getOrDefault(value)
