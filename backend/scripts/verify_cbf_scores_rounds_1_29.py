"""Read-only comparison of 2026 Série B provider scores against the official CBF score table.

The CBF basic schedule PDF updated 23 September 2026 contains final scores for rounds 1–29.
It does not contain final scores for rounds 30–38. This audit only certifies rows actually
carrying a score in that source; it never infers missing scores.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

import psycopg

PROVIDER = "5DollarFootballAPI"
SOURCE_ID = "5dollarfootballapi"
COMPETITION_ID = "522514093"
DATABASE = "veltrix_ai_analyst"
CBF_PDF_URL = (
    "https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/"
    "Tabela_Detalhada_Brasileiro_Serie_B_2026_23_09_378b396600.pdf"
)
CBF_PDF_UPDATED = "2026-09-23"
EXPECTED_SCORED_FIXTURES = 290

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
SELECT provider_fixture_id, home_team_provider_id, away_team_provider_id,
       home_team_name, away_team_name, home_goals, away_goals
FROM veltrix_ai_analyst.provider_fixtures
WHERE provider = %s AND source_id = %s
  AND provider_competition_id = %s AND status = 'FINISHED'
"""


def norm(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def split_club_and_state(tokens: list[str], *, away: bool) -> list[str]:
    state_codes = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }
    if away:
        for index, token in enumerate(tokens):
            if token in state_codes:
                return tokens[:index]
    elif tokens and tokens[-1] in state_codes:
        return tokens[:-1]
    raise ValueError(f"team state suffix not found: {tokens}")


def parse_scored_row(tokens: list[str]) -> dict[str, object] | None:
    """Parse one CBF visual row; return None for headings or unscored fixtures."""
    if not tokens or not re.fullmatch(r"\d{3}", tokens[0]):
        return None
    try:
        separator = tokens.index("x", 1)
    except ValueError:
        return None
    if separator < 3 or separator + 2 >= len(tokens):
        return None
    home_goals_token = tokens[separator - 1]
    away_goals_token = tokens[separator + 1]
    if not home_goals_token.isdigit() or not away_goals_token.isdigit():
        return None
    metadata_tokens = {"seg", "ter", "qua", "qui", "sex", "sab", "sáb", "dom"}
    home_raw = [
        token for token in tokens[1 : separator - 1]
        if not re.fullmatch(r"(?:[0-9]{1,2}ª?|[0-9]{2}/[0-9]{2}|[0-9]{2}:[0-9]{2})", token)
        and token.casefold() not in metadata_tokens
    ]
    home_tokens = split_club_and_state(home_raw, away=False)
    away_tokens = split_club_and_state(tokens[separator + 2 :], away=True)
    home_label = " ".join(home_tokens)
    away_label = " ".join(away_tokens)
    return {
        "cbf_reference": tokens[0].lstrip("0") or "0",
        "home_label": home_label,
        "away_label": away_label,
        "home_team_provider_id": CBF_LABEL_TO_PROVIDER_TEAM_ID.get(norm(home_label)),
        "away_team_provider_id": CBF_LABEL_TO_PROVIDER_TEAM_ID.get(norm(away_label)),
        "home_goals": int(home_goals_token),
        "away_goals": int(away_goals_token),
    }


def parse_cbf_pdf(pdf_bytes: bytes) -> list[dict[str, object]]:
    import pymupdf as fitz

    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    fixtures: list[dict[str, object]] = []
    for page in document:
        words = sorted(
            page.get_text("words"),
            key=lambda word: (float(word[1]), float(word[0])),
        )
        rows: list[dict[str, object]] = []
        for word in words:
            y = float(word[1])
            if not rows or abs(y - float(rows[-1]["baseline"])) > 2.0:
                rows.append({"baseline": y, "ys": [y], "words": []})
            rows[-1]["words"].append((float(word[0]), str(word[4])))
            rows[-1]["ys"].append(y)
            rows[-1]["baseline"] = sum(rows[-1]["ys"]) / len(rows[-1]["ys"])
        for row in rows:
            tokens = [token for _, token in sorted(row["words"])]
            try:
                fixture = parse_scored_row(tokens)
            except ValueError:
                continue
            if fixture is not None:
                fixtures.append(fixture)
    references = [str(row["cbf_reference"]) for row in fixtures]
    if len(references) != len(set(references)):
        raise RuntimeError("DUPLICATE_CBF_SCORE_REFERENCES_IN_SOURCE")
    return fixtures


def download_pdf() -> bytes:
    request = Request(CBF_PDF_URL, headers={"User-Agent": "VELTRIX-CBF-Score-Audit/1.0"})
    with urlopen(request, timeout=45) as response:
        if response.status != 200:
            raise RuntimeError(f"CBF_PDF_HTTP_{response.status}")
        return response.read()


def load_score_adjudications() -> dict[str, dict[str, object]]:
    registry_path = Path(__file__).resolve().parents[1] / "data/research/official_score_adjudications.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entries = registry.get("adjudications", [])
    adjudications = {str(row["cbf_reference"]): row for row in entries}
    if len(adjudications) != len(entries):
        raise RuntimeError("DUPLICATE_OFFICIAL_SCORE_ADJUDICATION_REFERENCE")
    return adjudications


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL_REQUIRED")
    if os.environ.get("EXPECTED_DATABASE_NAME", DATABASE) != DATABASE:
        raise SystemExit("EXPECTED_DATABASE_NAME_MISMATCH")

    pdf_bytes = download_pdf()
    cbf_fixtures = parse_cbf_pdf(pdf_bytes)
    if len(cbf_fixtures) != EXPECTED_SCORED_FIXTURES:
        raise SystemExit(f"EXPECTED_{EXPECTED_SCORED_FIXTURES}_SCORED_ROWS_GOT_{len(cbf_fixtures)}")

    with psycopg.connect(database_url) as connection:
        if connection.info.dbname != DATABASE:
            raise SystemExit("DATABASE_TARGET_MISMATCH")
        with connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            provider_rows = connection.execute(
                FIXTURE_QUERY, (PROVIDER, SOURCE_ID, COMPETITION_ID)
            ).fetchall()

    score_adjudications = load_score_adjudications()
    consumed_adjudications: set[str] = set()
    provider_by_pair: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for fixture_id, home_id, away_id, home_name, away_name, home_goals, away_goals in provider_rows:
        provider_by_pair[(str(home_id), str(away_id))].append({
            "provider_fixture_id": str(fixture_id),
            "home_team_name": home_name,
            "away_team_name": away_name,
            "home_goals": home_goals,
            "away_goals": away_goals,
        })

    verified = []
    adjudicated = []
    mismatches = []
    missing = []
    ambiguous = []
    unmapped = []
    for cbf in cbf_fixtures:
        home_id = cbf["home_team_provider_id"]
        away_id = cbf["away_team_provider_id"]
        if not home_id or not away_id:
            unmapped.append(cbf)
            continue
        candidates = provider_by_pair.get((str(home_id), str(away_id)), [])
        if not candidates:
            missing.append(cbf)
            continue
        if len(candidates) != 1:
            ambiguous.append({**cbf, "provider_candidates": candidates})
            continue
        provider = candidates[0]
        expected_score = (int(cbf["home_goals"]), int(cbf["away_goals"]))
        provider_score = (provider["home_goals"], provider["away_goals"])
        audit_row = {
            **cbf,
            "provider_fixture_id": provider["provider_fixture_id"],
            "provider_home_name": provider["home_team_name"],
            "provider_away_name": provider["away_team_name"],
            "provider_score": list(provider_score),
            "cbf_score": list(expected_score),
        }
        if provider_score == expected_score:
            verified.append(audit_row)
            continue
        adjudication = score_adjudications.get(str(cbf["cbf_reference"]))
        if adjudication is not None:
            official_score = tuple(int(value) for value in adjudication["official_score"])
            pdf_score = tuple(int(value) for value in adjudication["pdf_score"])
            official_page = str(adjudication["official_match_page_url"])
            if (
                str(adjudication["provider_fixture_id"]) != provider["provider_fixture_id"]
                or pdf_score != expected_score
                or official_score != provider_score
                or "cbf.com.br/futebol-brasileiro/jogos/" not in official_page
            ):
                mismatches.append({**audit_row, "adjudication_validation": "FAILED"})
            else:
                consumed_adjudications.add(str(cbf["cbf_reference"]))
                adjudicated.append({
                    **audit_row,
                    "pdf_score": list(expected_score),
                    "official_match_page_score": list(official_score),
                    "official_match_page_url": official_page,
                    "corroborating_official_news_url": adjudication.get(
                        "corroborating_official_cbf_news_url"
                    ),
                    "adjudication_status": adjudication["status"],
                    "reason": adjudication["reason"],
                })
        else:
            mismatches.append(audit_row)

    unused_adjudications = sorted(set(score_adjudications) - consumed_adjudications)
    counts = {
        "cbf_scored_rows": len(cbf_fixtures),
        "provider_finished_rows": len(provider_rows),
        "pdf_exact_score_matches": len(verified),
        "official_match_page_score_adjudications": len(adjudicated),
        "verified_against_controlling_official_cbf_evidence": len(verified) + len(adjudicated),
        "unresolved_score_mismatches": len(mismatches),
        "provider_pairing_missing": len(missing),
        "multiple_provider_candidates": len(ambiguous),
        "unmapped_cbf_teams": len(unmapped),
        "unused_score_adjudications": len(unused_adjudications),
    }
    passed = (
        len(cbf_fixtures) == EXPECTED_SCORED_FIXTURES
        and len(verified) + len(adjudicated) == EXPECTED_SCORED_FIXTURES
        and not mismatches and not missing and not ambiguous and not unmapped
        and not unused_adjudications
    )
    output = {
        "audit_type": "OFFICIAL_CBF_PUBLISHED_SCORE_TABLE_VS_5DOLLAR_FINISHED_FIXTURES_READ_ONLY",
        "database": DATABASE,
        "provider": PROVIDER,
        "source_id": SOURCE_ID,
        "competition_id": COMPETITION_ID,
        "cbf_source_url": CBF_PDF_URL,
        "cbf_source_updated": CBF_PDF_UPDATED,
        "cbf_pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "score_scope": "Rounds 1–29 only; later rounds have no score in this PDF and are not inferred.",
        "passed": passed,
        "counts": counts,
        "verified_pdf_exact_matches": verified,
        "official_match_page_adjudications": adjudicated,
        "mismatches": mismatches,
        "unused_score_adjudications": unused_adjudications,
        "missing": missing,
        "ambiguous": ambiguous,
        "unmapped": unmapped,
        "limitations": [
            "The CBF basic-schedule PDF is the primary score source; individual CBF match pages control where a documented source conflict exists.",
            "The one PDF conflict at match 245 is adjudicated to the individual official CBF match page, corroborated by an official CBF round article; raw PDF and provider rows remain unchanged.",
            "The PDF is updated 2026-09-23 and carries scores for rounds 1–29 only.",
            "This does not verify scores for rounds 30–38.",
            "Candidate provider-team mapping is used only to pair fixtures; no canonical identity is approved.",
            "No production rows are modified and this does not establish PIT availability.",
        ],
    }
    out = Path(os.environ.get(
        "CBF_SCORE_VERIFICATION_PATH",
        "artifacts/cbf-score-verification-rounds-1-29.json",
    ))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASSED" if passed else "FAILED", "counts": counts, "output": str(out)}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
