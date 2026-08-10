"""Smoke test: the migrations and the models describe the same database.

This is the failure that only appears in production. Development runs on
`create_all`, which builds the schema straight from the models, so a column
added to a model without a migration works perfectly on every machine that has
ever run the app -- and is missing the moment a migrated database is used.

The symptom is an UndefinedColumn error on a query that has passed every test.

Comparing the two is therefore worth doing directly: build one database from
Alembic and one from the models, and require them to match.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_schema_drift.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from sqlalchemy import create_engine, inspect  # noqa: E402

from db.base import Base  # noqa: E402
import models  # noqa: E402,F401  (imports every model so metadata is complete)

BACKEND = Path(__file__).resolve().parent.parent

#: Alembic's own bookkeeping, present in a migrated database and absent from
#: the models by design.
IGNORED_TABLES = {"alembic_version"}


def _migrated_schema(db_path: Path) -> dict[str, set[str]]:
    """Build a database with `alembic upgrade head` and describe it."""
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        inspector = inspect(engine)
        return {
            table: {column["name"] for column in inspector.get_columns(table)}
            for table in inspector.get_table_names()
            if table not in IGNORED_TABLES
        }
    finally:
        engine.dispose()


def _model_schema(db_path: Path) -> dict[str, set[str]]:
    """Build a database with create_all and describe it."""
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        Base.metadata.create_all(engine)
        inspector = inspect(engine)
        return {
            table: {column["name"] for column in inspector.get_columns(table)}
            for table in inspector.get_table_names()
            if table not in IGNORED_TABLES
        }
    finally:
        engine.dispose()


def check_no_drift() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        migrated = _migrated_schema(Path(tmp) / "migrated.db")
        modelled = _model_schema(Path(tmp) / "modelled.db")

    only_in_models = sorted(set(modelled) - set(migrated))
    only_in_migrations = sorted(set(migrated) - set(modelled))

    assert not only_in_models, (
        f"tables in the models with no migration: {only_in_models}. "
        "These work on every development machine and do not exist in "
        "production."
    )
    assert not only_in_migrations, (
        f"tables created by a migration but absent from the models: "
        f"{only_in_migrations}. Either the model was deleted without a "
        f"migration, or the migration created something nothing uses."
    )

    mismatches: list[str] = []
    for table in sorted(modelled):
        missing_in_migration = sorted(modelled[table] - migrated[table])
        missing_in_models = sorted(migrated[table] - modelled[table])
        if missing_in_migration:
            mismatches.append(
                f"{table}: {missing_in_migration} in the model with no migration"
            )
        if missing_in_models:
            mismatches.append(
                f"{table}: {missing_in_models} in the migration with no model field"
            )

    assert not mismatches, "schema drift:\n  " + "\n  ".join(mismatches)


def check_downgrade_is_complete() -> None:
    """Every migration reverses cleanly, all the way to empty.

    A downgrade nobody has run is a rollback plan nobody has. This is the
    cheapest possible check that the plan exists.
    """
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "roundtrip.db"
        env = {
            **os.environ,
            "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}",
        }
        for command in (["upgrade", "head"], ["downgrade", "base"]):
            result = subprocess.run(
                [sys.executable, "-m", "alembic", *command],
                cwd=BACKEND,
                env=env,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (command, result.stderr)

        engine = create_engine(f"sqlite:///{db_path.as_posix()}")
        try:
            remaining = {
                table
                for table in inspect(engine).get_table_names()
                if table not in IGNORED_TABLES
            }
        finally:
            engine.dispose()

        assert not remaining, f"downgrade left tables behind: {sorted(remaining)}"


def run() -> None:
    check_no_drift()
    check_downgrade_is_complete()

    print("SCHEMA DRIFT SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
