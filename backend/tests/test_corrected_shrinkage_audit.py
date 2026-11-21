import ast
from pathlib import Path

from app.research.corrected_shrinkage_audit import (
    ARCHIVED_CONFIG, FOLD_RULE, HOME_ADVANTAGE_TREATMENT, REFERENCE_K,
)


def test_preregistered_design_is_frozen():
    assert REFERENCE_K == (0.5, 2.0)
    assert ARCHIVED_CONFIG == {"team_ridge": 0.5, "competition_ridge": 0.5, "half_life_days": 365.0}
    assert "60%" in FOLD_RULE and "90%" in FOLD_RULE
    assert HOME_ADVANTAGE_TREATMENT == "unpenalized in archived and both reference fits"


def test_audit_module_has_no_database_or_provider_imports():
    path = Path(__file__).parents[1] / "app" / "research" / "corrected_shrinkage_audit.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = ("psycopg", "sqlalchemy", "httpx", "requests", "app.db", "app.providers")
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(any(token in name for token in forbidden) for name in imports)
