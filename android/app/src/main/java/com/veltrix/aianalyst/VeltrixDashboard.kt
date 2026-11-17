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
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material3.Icon
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
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

/* ---------- Theme (iOS system colors) ---------- */

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

/** Android has no SF Pro. Sans-serif is the closest system font; swap in Inter for a closer match. */
private val Font = FontFamily.SansSerif

private fun t(size: Int, w: FontWeight = FontWeight.Normal, c: Color) =
    TextStyle(fontFamily = Font, fontSize = size.sp, fontWeight = w, color = c)

/* ---------- Sample data (replace with backend data later) ---------- */

private data class Match(
    val teams: String, val league: String,
    val h: Int, val d: Int, val a: Int,
    val btts: Int, val o15: Int, val o25: Int, val o35: Int,
    val odds: Double, val pick: String,
) {
    val pickProb get() = when (pick) { "1" -> h; "X" -> d; else -> a }
    val pickLabel get() = when (pick) { "1" -> "Home"; "X" -> "Draw"; else -> "Away" }
    val edge get() = (pickProb / 100.0 * odds - 1) * 100
}

private data class Result(val teams: String, val score: String, val pick: String, val won: Boolean)

private val matches = listOf(
    Match("Arsenal vs Brighton", "Premier League · 17:30", 62, 23, 15, 48, 86, 64, 38, 1.85, "1"),
    Match("Inter vs Napoli", "Serie A · 19:45", 44, 29, 27, 61, 84, 58, 31, 2.30, "1"),
    Match("Girona vs Betis", "La Liga · 20:00", 36, 28, 36, 67, 85, 62, 35, 2.60, "X"),
    Match("Leverkusen vs Mainz", "Bundesliga · 20:30", 70, 18, 12, 55, 91, 72, 49, 1.60, "1"),
    Match("Lyon vs Nice", "Ligue 1 · 21:00", 41, 30, 29, 52, 80, 51, 27, 2.45, "1"),
)

private val history = listOf(
    Result("Chelsea vs Spurs", "2-1", "1", true),
    Result("Roma vs Lazio", "1-1", "X", true),
    Result("Sevilla vs Valencia", "0-2", "1", false),
    Result("Dortmund vs Köln", "3-0", "1", true),
    Result("PSG vs Lille", "1-0", "1", true),
    Result("Milan vs Torino", "1-2", "1", false),
)

/* ---------- Tabs ---------- */

private enum class Tab(val label: String, val icon: ImageVector) {
    Home("Home", Icons.Filled.Home),
    History("History", Icons.Filled.History),
    Btts("BTTS", Icons.Filled.CheckCircle),
    Value("Value Bet", Icons.Filled.TrendingUp),
    OverUnder("Over/Under", Icons.Filled.BarChart),
    Menu("Menu", Icons.Filled.Menu),
}

/* ---------- Entry point ---------- */

@Composable
fun VeltrixDashboard() {
    val pal = if (isSystemInDarkTheme()) DarkPal else LightPal
    var tab by remember { mutableStateOf(Tab.Home) }

    CompositionLocalProvider(LocalPal provides pal) {
        Box(Modifier.fillMaxSize().background(pal.bg)) {
            when (tab) {
                Tab.Home -> HomeScreen()
                Tab.History -> HistoryScreen()
                Tab.Btts -> BttsScreen()
                Tab.Value -> ValueScreen()
                Tab.OverUnder -> OverUnderScreen()
                Tab.Menu -> MenuScreen()
            }
            BottomMenu(tab, { tab = it }, Modifier.align(Alignment.BottomCenter))
        }
    }
}

/* ---------- Bottom menu box ---------- */

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
                Text(
                    item.label,
                    style = t(10, FontWeight.Medium, if (on) p.blue else p.sub),
                    maxLines = 1,
                )
            }
        }
    }
}

/* ---------- Shared pieces ---------- */

@Composable
private fun Screen(title: String, subtitle: String, content: @Composable ColumnScope.() -> Unit) {
    val p = LocalPal.current
    LazyColumn(
        Modifier.fillMaxSize().statusBarsPadding(),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 14.dp, bottom = 120.dp),
    ) {
        item {
            Text(title, style = t(34, FontWeight.Bold, p.text))
            Text(subtitle, style = t(15, c = p.sub), modifier = Modifier.padding(top = 2.dp, bottom = 14.dp))
            Column(content = content)
        }
    }
}

@Composable
private fun Card(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(LocalPal.current.card),
        content = content,
    )
}

@Composable
private fun Divider() = Box(Modifier.fillMaxWidth().height(0.5.dp).background(LocalPal.current.line))

@Composable
private fun SectionTitle(text: String) =
    Text(text, style = t(22, FontWeight.Bold, LocalPal.current.text),
        modifier = Modifier.padding(start = 4.dp, top = 22.dp, bottom = 8.dp))

@Composable
private fun Pill(text: String, color: Color) {
    Text(
        text,
        style = t(13, FontWeight.SemiBold, color),
        modifier = Modifier.clip(CircleShape).background(color.copy(alpha = 0.16f))
            .padding(horizontal = 10.dp, vertical = 4.dp),
    )
}

@Composable
private fun StatTile(value: String, label: String, color: Color, modifier: Modifier) {
    val p = LocalPal.current
    Column(modifier.clip(RoundedCornerShape(14.dp)).background(p.card).padding(14.dp)) {
        Text(value, style = t(28, FontWeight.Bold, color))
        Text(label, style = t(13, c = p.sub))
    }
}

@Composable
private fun SplitBar(parts: List<Pair<Int, Color>>) {
    Row(Modifier.fillMaxWidth().padding(top = 12.dp, bottom = 6.dp).height(8.dp)
        .clip(RoundedCornerShape(4.dp)), horizontalArrangement = Arrangement.spacedBy(2.dp)) {
        parts.forEach { (w, c) -> Box(Modifier.weight(w.coerceAtLeast(1).toFloat()).fillMaxHeight().background(c)) }
    }
}

@Composable
private fun Legend(items: List<Pair<String, String>>) {
    val p = LocalPal.current
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        items.forEach { (k, v) ->
            Row { Text("$k ", style = t(13, c = p.sub)); Text(v, style = t(13, FontWeight.SemiBold, p.text)) }
        }
    }
}

@Composable
private fun MatchHeader(teams: String, meta: String, trailing: @Composable () -> Unit) {
    val p = LocalPal.current
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
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
            val s = 6.dp.toPx()
            val box = Size(this.size.width - s, this.size.height - s)
            val tl = Offset(s / 2, s / 2)
            drawArc(p.fill, 0f, 360f, false, tl, box, style = Stroke(s))
            drawArc(color, -90f, percent * 3.6f, false, tl, box, style = Stroke(s, cap = StrokeCap.Round))
        }
        Text("$percent%", style = t(14, FontWeight.Bold, p.text))
    }
}

/* ---------- Screens ---------- */

@Composable
private fun HomeScreen() {
    val p = LocalPal.current
    Screen("Veltrix", "AI match analysis · Today") {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatTile("68%", "1X2 accuracy (30d)", p.green, Modifier.weight(1f))
            StatTile("12", "Matches analysed", p.blue, Modifier.weight(1f))
        }
        Spacer(Modifier.height(10.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatTile("4", "Value bets found", p.orange, Modifier.weight(1f))
            StatTile("+8.4u", "Profit this week", p.text, Modifier.weight(1f))
        }
        SectionTitle("Today's predictions")
        Card {
            matches.forEachIndexed { i, m ->
                if (i > 0) Divider()
                Column(Modifier.padding(16.dp)) {
                    MatchHeader(m.teams, m.league) { Pill(m.pickLabel, p.blue) }
                    SplitBar(listOf(m.h to p.blue, m.d to p.sub, m.a to p.orange))
                    Legend(listOf("1" to "${m.h}%", "X" to "${m.d}%", "2" to "${m.a}%"))
                }
            }
        }
    }
}

@Composable
private fun HistoryScreen() {
    val p = LocalPal.current
    Screen("History", "Past predictions and results") {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatTile("41", "Won", p.green, Modifier.weight(1f))
            StatTile("19", "Lost", p.red, Modifier.weight(1f))
        }
        Spacer(Modifier.height(14.dp))
        Card {
            history.forEachIndexed { i, r ->
                if (i > 0) Divider()
                Box(Modifier.padding(16.dp)) {
                    MatchHeader(r.teams, "Final ${r.score} · Predicted ${r.pick}") {
                        Pill(if (r.won) "Won" else "Lost", if (r.won) p.green else p.red)
                    }
                }
            }
        }
    }
}

@Composable
private fun BttsScreen() {
    val p = LocalPal.current
    Screen("BTTS", "Both teams to score") {
        Card {
            matches.sortedByDescending { it.btts }.forEachIndexed { i, m ->
                if (i > 0) Divider()
                Box(Modifier.padding(16.dp)) {
                    MatchHeader(m.teams, m.league) { Ring(m.btts, if (m.btts >= 60) p.green else p.orange) }
                }
            }
        }
    }
}

@Composable
private fun ValueScreen() {
    val p = LocalPal.current
    val bets = matches.filter { it.edge > 0 }.sortedByDescending { it.edge }
    Screen("Value Bets", "Where our probability beats the bookmaker") {
        Card {
            if (bets.isEmpty()) {
                Text("No value bets right now. Check again after odds update.",
                    style = t(13, c = p.sub), modifier = Modifier.padding(16.dp))
            }
            bets.forEachIndexed { i, m ->
                if (i > 0) Divider()
                Column(Modifier.padding(16.dp)) {
                    MatchHeader(m.teams, "${m.pickLabel} @ ${"%.2f".format(m.odds)}") {
                        Pill("+${"%.1f".format(m.edge)}% edge", p.green)
                    }
                    Row(Modifier.fillMaxWidth().padding(top = 12.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Mini("Our probability", "${m.pickProb}%", Modifier.weight(1f))
                        Mini("Bookmaker implied", "${(100 / m.odds).toInt()}%", Modifier.weight(1f))
                    }
                }
            }
        }
    }
}

@Composable
private fun Mini(label: String, value: String, modifier: Modifier) {
    val p = LocalPal.current
    Column(modifier.clip(RoundedCornerShape(10.dp)).background(p.bg).padding(10.dp)) {
        Text(label, style = t(12, c = p.sub))
        Text(value, style = t(20, FontWeight.Bold, p.text), modifier = Modifier.padding(top = 2.dp))
    }
}

@Composable
private fun OverUnderScreen() {
    val p = LocalPal.current
    var line by remember { mutableStateOf("2.5") }
    Screen("Over / Under", "Total goals") {
        Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(9.dp)).background(p.fill).padding(2.dp)) {
            listOf("1.5", "2.5", "3.5").forEach { l ->
                val on = l == line
                Box(
                    Modifier.weight(1f).clip(RoundedCornerShape(7.dp))
                        .background(if (on) p.card else Color.Transparent)
                        .clickable { line = l }.padding(vertical = 7.dp),
                    contentAlignment = Alignment.Center,
                ) { Text(l, style = t(13, FontWeight.SemiBold, p.text)) }
            }
        }
        Spacer(Modifier.height(14.dp))
        Card {
            matches.forEachIndexed { i, m ->
                if (i > 0) Divider()
                val over = when (line) { "1.5" -> m.o15; "3.5" -> m.o35; else -> m.o25 }
                val under = 100 - over
                Column(Modifier.padding(16.dp)) {
                    MatchHeader(m.teams, m.league) {
                        Pill(if (over >= 50) "Over $line" else "Under $line", if (over >= 50) p.green else p.orange)
                    }
                    SplitBar(listOf(over to p.green, under to p.red))
                    Legend(listOf("Over" to "$over%", "Under" to "$under%"))
                }
            }
        }
    }
}

@Composable
private fun MenuScreen() {
    Screen("Menu", "Veltrix AI Analyst") {
        Card {
            ToggleRow("Notifications", true); Divider()
            ToggleRow("Value bet alerts", true)
        }
        SectionTitle("Model")
        Card {
            InfoRow("Minimum edge", "5%"); Divider()
            InfoRow("Leagues", "All"); Divider()
            InfoRow("Odds format", "Decimal"); Divider()
            InfoRow("Version", "0.1.0")
        }
    }
}

@Composable
private fun ToggleRow(label: String, initial: Boolean) {
    val p = LocalPal.current
    var on by remember { mutableStateOf(initial) }
    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Text(label, style = t(17, c = p.text))
        Switch(on, { on = it }, colors = SwitchDefaults.colors(
            checkedTrackColor = p.green, checkedThumbColor = Color.White, checkedBorderColor = p.green,
            uncheckedTrackColor = p.fill, uncheckedThumbColor = Color.White, uncheckedBorderColor = p.fill))
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    val p = LocalPal.current
    Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = t(17, c = p.text))
        Text(value, style = t(17, c = p.sub))
    }
}
