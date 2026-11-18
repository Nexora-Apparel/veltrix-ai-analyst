"""Read-only CBF schedule reconciliation for Série B 2026 rounds 1–18.

This compares provider-local fixture identities against three official CBF detailed
schedule PDFs. It does not mutate provider/canonical rows and does not certify scores,
team identities, or historical point-in-time availability.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import fitz
import psycopg

PROVIDER = "5DollarFootballAPI"
SOURCE_ID = "5dollarfootballapi"
COMPETITION_ID = "522514093"
DATABASE = "veltrix_ai_analyst"
LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
PDFS = (
    {
        "rounds": [1, 2, 3, 4, 5],
        "url": "https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_Brasileirao_Serie_B_2026_Rodadas_1_a_5_8495da2f30.pdf",
        "published": "2026-03-07",
    },
    {
        "rounds": [6, 7, 8, 9, 10, 11],
        "url": "https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_6_a_11_rodada_Brasileiro_Serie_B_d95c40657d.pdf",
        "published": "2026-04-08",
    },
    {
        "rounds": [12, 13, 14, 15, 16, 17, 18],
        "url": "https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_12_a_18_rodada_Brasileiro_Serie_B_2026_ea9e84afde.pdf",
        "published": "2026-05-28",
    },
)

# Candidate schedule labels from the existing CBF review matrix. This is a
# provider-local comparison map only; it does not approve canonical identities.
CBF_LABEL_TO_PROVIDER_TEAM_ID = {
    "america": "1102583842",
    "avai": "1446563615",
    "ponte preta": "1548718709",
    "novorizontino": "1620921678",
    "ceara": "1657329649",
    "atletico": "1684426968",
    "operario": "2016651568",
    "vila nova": "2434042650",
    "crb": "2651466053",
    "juventude": "2672186301",
    "athletic": "3007875643",
    "goias": "3126624865",
    "londrina": "3219034225",
    "botafogo": "3250670103",
    "criciuma": "3324195045",
    "cuiaba": "4227927162",
    "nautico": "4267737771",
    "sport": "559667509",
    "fortaleza": "744720326",
    "sao bernardo fc": "844813267",
}
FIXTURE_QUERY = """
SELECT provider_fixture_id, kickoff_at, home_team_provider_id,
       away_team_provider_id, home_team_name, away_team_name,
       home_goals, away_goals, status
FROM veltrix_ai_analyst.provider_fixtures
WHERE provider = %s AND source_id = %s
  AND provider_competition_id = %s
  AND status = 'FINISHED'
ORDER BY kickoff_at, provider_fixture_id
"""


def norm(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def download_pdf(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "VELTRIX-CBF-Schedule-Audit/1.0"})
    with urlopen(request, timeout=30) as response:
        return response.read()


def split_club_and_state(tokens: list[str], *, away: bool) -> list[str]:
    if away:
        for index, token in enumerate(tokens):
            if re.fullmatch(r"[A-Z]{2}", token):
                return tokens[:index]
        raise ValueError(f"away team state suffix not found: {tokens}")
    if tokens and re.fullmatch(r"[A-Z]{2}", tokens[-1]):
        return tokens[:-1]
    raise ValueError(f"home team state suffix not found: {tokens}")


def parse_pdf(pdf_bytes: bytes, source: dict[str, object]) -> list[dict[str, object]]:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    fixtures: list[dict[str, object]] = []
    for page in document:
        # PDF table cells are separate text blocks. Reconstruct visual rows by
        # baseline (y-coordinate), then sort each row from left to right.
        words = sorted(page.get_text("words"), key=lambda word: (float(word[1]), float(word[0])))
        visual_rows: list[dict[str, object]] = []
        for word in words:
            y = float(word[1])
            if not visual_rows or abs(y - float(visual_rows[-1]["baseline"])) > 2.0:
                visual_rows.append({"baseline": y, "ys": [y], "words": []})
            visual_rows[-1]["words"].append((float(word[0]), str(word[4])))
            visual_rows[-1]["ys"].append(y)
            visual_rows[-1]["baseline"] = sum(visual_rows[-1]["ys"]) / len(visual_rows[-1]["ys"])
        for visual_row in visual_rows:
            tokens = [token for _, token in sorted(visual_row["words"])]
            if len(tokens) < 9 or not re.fullmatch(r"\d{3}", tokens[0]):
                continue
            round_match = re.fullmatch(r"(\d{1,2})ª?", tokens[1])
            date_match = re.fullmatch(r"(\d{2})/(\d{2})", tokens[2])
            if not round_match or not date_match or not re.fullmatch(r"\d{2}:\d{2}", tokens[4]):
                continue
            round_number = int(round_match.group(1))
            if round_number not in source["rounds"]:
                continue
            try:
                cross = tokens.index("x", 5)
                home_tokens = split_club_and_state(tokens[5:cross], away=False)
                away_tokens = split_club_and_state(tokens[cross + 1:], away=True)
                home_label = " ".join(home_tokens)
                away_label = " ".join(away_tokens)
                home_key, away_key = norm(home_label), norm(away_label)
                home_id = CBF_LABEL_TO_PROVIDER_TEAM_ID.get(home_key)
                away_id = CBF_LABEL_TO_PROVIDER_TEAM_ID.get(away_key)
                local_dt = datetime.strptime(
                    f"{date_match.group(1)}/{date_match.group(2)}/2026 {tokens[4]}",
                    "%d/%m/%Y %H:%M",
                ).replace(tzinfo=LOCAL_TZ)
            except (ValueError, IndexError):
                continue
            fixtures.append({
                "cbf_reference": tokens[0].lstrip("0") or "0",
                "round": round_number,
                "home_label": home_label,
                "away_label": away_label,
                "home_team_provider_id": home_id,
                "away_team_provider_id": away_id,
                "official_local_kickoff": local_dt.isoformat(),
                "official_utc_kickoff": local_dt.astimezone(ZoneInfo("UTC")).isoformat(),
                "schedule_published": source["published"],
                "schedule_pdf_url": source["url"],
            })
    return fixtures


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL_REQUIRED")
    if os.environ.get("EXPECTED_DATABASE_NAME", DATABASE) != DATABASE:
        raise SystemExit("EXPECTED_DATABASE_NAME_MISMATCH")

    schedule: list[dict[str, object]] = []
    pdf_audit = []
    for source in PDFS:
        content = download_pdf(str(source["url"]))
        parsed = parse_pdf(content, source)
        schedule.extend(parsed)
        pdf_audit.append({
            "url": source["url"],
            "published": source["published"],
            "sha256": hashlib.sha256(content).hexdigest(),
            "parsed_fixture_rows": len(parsed),
        })

    with psycopg.connect(database_url) as connection:
        if connection.info.dbname != DATABASE:
            raise SystemExit("DATABASE_TARGET_MISMATCH")
        with connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            rows = connection.execute(
                FIXTURE_QUERY, (PROVIDER, SOURCE_ID, COMPETITION_ID)
            ).fetchall()

    provider_by_pair: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for fixture_id, kickoff, home_id, away_id, home_name, away_name, hg, ag, status in rows:
        provider_by_pair[(str(home_id), str(away_id))].append({
            "provider_fixture_id": str(fixture_id),
            "kickoff_at": kickoff,
            "home_team_name": home_name,
            "away_team_name": away_name,
            "home_goals": hg,
            "away_goals": ag,
            "status": status,
        })

    results = []
    for expected in sorted(schedule, key=lambda row: (row["round"], row["cbf_reference"])):
        home_id, away_id = expected["home_team_provider_id"], expected["away_team_provider_id"]
        if not home_id or not away_id:
            results.append({**expected, "result": "UNMAPPED_CBF_TEAM_LABEL"})
            continue
        candidates = provider_by_pair.get((home_id, away_id), [])
        if len(candidates) == 0:
            results.append({**expected, "result": "PROVIDER_PAIRING_NOT_FOUND"})
            continue
        if len(candidates) > 1:
            results.append({**expected, "result": "MULTIPLE_PROVIDER_PAIRING_CANDIDATES",
                            "provider_candidates": candidates})
            continue
        candidate = candidates[0]
        provider_local = candidate["kickoff_at"].astimezone(LOCAL_TZ)
        expected_local = datetime.fromisoformat(str(expected["official_local_kickoff"]))
        results.append({
            **expected,
            "provider_fixture_id": candidate["provider_fixture_id"],
            "provider_home_name": candidate["home_team_name"],
            "provider_away_name": candidate["away_team_name"],
            "provider_kickoff_at": candidate["kickoff_at"].isoformat(),
            "provider_local_kickoff": provider_local.isoformat(),
            "provider_score": [candidate["home_goals"], candidate["away_goals"]],
            "result": (
                "PAIRING_AND_KICKOFF_MATCH"
                if provider_local.strftime("%Y-%m-%d %H:%M") == expected_local.strftime("%Y-%m-%d %H:%M")
                else "PAIRING_MATCH_KICKOFF_DIFFERS_FROM_INITIAL_CBF_SCHEDULE"
            ),
        })

    per_round = {}
    for round_number in range(1, 19):
        group = [row for row in results if row["round"] == round_number]
        per_round[str(round_number)] = {
            "expected": len(group),
            "pairing_and_kickoff_match": sum(r["result"] == "PAIRING_AND_KICKOFF_MATCH" for r in group),
            "kickoff_differs_from_initial_schedule": sum(r["result"] == "PAIRING_MATCH_KICKOFF_DIFFERS_FROM_INITIAL_CBF_SCHEDULE" for r in group),
            "pairing_missing": sum(r["result"] == "PROVIDER_PAIRING_NOT_FOUND" for r in group),
            "multiple_candidates": sum(r["result"] == "MULTIPLE_PROVIDER_PAIRING_CANDIDATES" for r in group),
            "unmapped_labels": sum(r["result"] == "UNMAPPED_CBF_TEAM_LABEL" for r in group),
        }

    output = {
        "audit_type": "READ_ONLY_INITIAL_CBF_SCHEDULE_RECONCILIATION_NOT_FINAL_SCHEDULE_OR_SCORE_CERTIFICATION",
        "database": DATABASE,
        "provider": PROVIDER,
        "source_id": SOURCE_ID,
        "competition_id": COMPETITION_ID,
        "scope": "CBF Serie B 2026 rounds 1–18",
        "schedule_pdf_sources": pdf_audit,
        "expected_fixture_rows": len(schedule),
        "provider_finished_rows_available": len(rows),
        "team_mapping_semantics": "CANDIDATE_PROVIDER_LOCAL_LABEL_MATCH_ONLY; NO_CANONICAL_IDENTITY_APPROVAL",
        "score_verification": "NOT_PERFORMED; PDF SCHEDULES DO NOT VERIFY FINAL SCORES",
        "kickoff_mismatch_semantics": "MAY_REFLECT_SUBSEQUENT_OFFICIAL_CBF_SCHEDULE_CHANGES; CHECK_CURRENT_CBF_MATCH_RECORD_BEFORE_ADJUDICATION",
        "per_round": per_round,
        "counts": {
            "pairing_and_kickoff_match": sum(r["result"] == "PAIRING_AND_KICKOFF_MATCH" for r in results),
            "kickoff_differs_from_initial_schedule": sum(r["result"] == "PAIRING_MATCH_KICKOFF_DIFFERS_FROM_INITIAL_CBF_SCHEDULE" for r in results),
            "pairing_missing": sum(r["result"] == "PROVIDER_PAIRING_NOT_FOUND" for r in results),
            "multiple_candidates": sum(r["result"] == "MULTIPLE_PROVIDER_PAIRING_CANDIDATES" for r in results),
            "unmapped_labels": sum(r["result"] == "UNMAPPED_CBF_TEAM_LABEL" for r in results),
        },
        "fixtures": results,
    }
    out = Path(os.environ.get("CBF_RECONCILIATION_PATH", "artifacts/cbf-rounds-1-18-reconciliation.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "CBF_ROUNDS_1_18_INITIAL_SCHEDULE_AUDIT_COMPLETE",
        "expected_fixture_rows": len(schedule),
        "provider_finished_rows_available": len(rows),
        "counts": output["counts"],
        "output": str(out),
    }, sort_keys=True))
    if len(schedule) != 180:
        raise SystemExit(f"EXPECTED_180_CBF_SCHEDULE_ROWS_GOT:{len(schedule)}")
    return 0


if __name__ == "__main__":
    main()
