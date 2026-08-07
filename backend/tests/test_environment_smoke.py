"""Smoke test: per-environment behaviour and the unsafe-config refusal.

Every assertion here is about a deployment that would otherwise work perfectly
and be insecure. That is the whole failure mode: nothing crashes, nothing logs,
and the signing key is one that anyone can read in the repository.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_environment.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from core.config import get_settings  # noqa: E402
from core.environment import (  # noqa: E402
    MIN_SECRET_LENGTH,
    Environment,
    UnsafeConfiguration,
    audit,
    enforce,
)


@dataclass
class FakeSettings:
    """A settings object shaped like the real one, safe by default."""

    app_env: str = "production"
    jwt_secret: str = "a" * 48
    seed_admin_password: str = "a-generated-admin-password"
    livekit_api_key: str = "real-key"
    livekit_api_secret: str = "a-real-livekit-secret-value"
    is_sqlite: bool = False
    rate_limit_enabled: bool = True
    cors_origins_list: list[str] = field(
        default_factory=lambda: ["https://app.example.com"]
    )


def check_environment_parsing() -> None:
    assert Environment.parse("development") is Environment.DEVELOPMENT
    assert Environment.parse("  Production ") is Environment.PRODUCTION
    assert Environment.parse("STAGING") is Environment.STAGING

    # A typo must not unlock the permissive path. Failing closed means a
    # refusal to start; failing open means running production on dev defaults.
    assert Environment.parse("prodcution") is Environment.PRODUCTION
    assert Environment.parse("") is Environment.PRODUCTION

    # Staging is held to production's rules: staging with production's
    # weaknesses tests nothing about production, and usually holds real data.
    assert Environment.STAGING.is_hardened
    assert Environment.PRODUCTION.is_hardened
    assert not Environment.DEVELOPMENT.is_hardened


def check_development_is_left_alone() -> None:
    """Development keeps its conveniences; that is the point of development."""
    dev = FakeSettings(
        app_env="development",
        jwt_secret="change_me_in_production",
        seed_admin_password="AdminPass123",
        is_sqlite=True,
        rate_limit_enabled=False,
        cors_origins_list=["*"],
    )
    assert audit(dev) == []
    enforce(dev)  # must not raise


def check_published_defaults_are_refused() -> None:
    for field_name, published in (
        ("jwt_secret", "change_me_in_production"),
        ("seed_admin_password", "AdminPass123"),
        ("livekit_api_key", "devkey"),
        ("livekit_api_secret", "secret"),
    ):
        settings = FakeSettings(**{field_name: published})
        problems = audit(settings)
        assert problems, field_name
        assert any(field_name.upper() in p for p in problems), (field_name, problems)


def check_weak_secret_is_refused() -> None:
    short = FakeSettings(jwt_secret="x" * (MIN_SECRET_LENGTH - 1))
    assert any("characters" in p for p in audit(short)), audit(short)

    exact = FakeSettings(jwt_secret="x" * MIN_SECRET_LENGTH)
    assert audit(exact) == []


def check_infrastructure_problems_are_refused() -> None:
    # SQLite in production is one file, one writer, and no backups worth the
    # name.
    assert any("SQLite" in p for p in audit(FakeSettings(is_sqlite=True)))

    # A wildcard origin with credentials is both a hole and, per the browser
    # spec, simply broken.
    assert any("CORS" in p for p in audit(FakeSettings(cors_origins_list=["*"])))

    assert any(
        "RATE_LIMIT" in p for p in audit(FakeSettings(rate_limit_enabled=False))
    )


def check_all_problems_reported_at_once() -> None:
    """Every reason, not the first.

    Otherwise a deployment is fixed one restart at a time, discovering the next
    problem after each one.
    """
    everything = FakeSettings(
        jwt_secret="change_me_in_production",
        seed_admin_password="AdminPass123",
        is_sqlite=True,
        rate_limit_enabled=False,
        cors_origins_list=["*"],
    )
    problems = audit(everything)
    assert len(problems) >= 5, problems

    try:
        enforce(everything)
    except UnsafeConfiguration as exc:
        message = str(exc)
        # The message has to be actionable on its own: whoever sees it is
        # looking at a container that will not start.
        assert "Refusing to start" in message
        assert "JWT_SECRET" in message and "CORS_ORIGINS" in message
        assert "APP_ENV=development" in message
    else:  # pragma: no cover
        raise AssertionError("an unsafe production configuration was accepted")


def check_docs_are_hidden_when_hardened() -> None:
    """Interactive docs hand an attacker a map of every endpoint."""
    settings = get_settings()
    assert settings.docs_enabled, "development should keep its docs"

    from core.config import Settings

    assert not Settings(app_env="production").docs_enabled
    assert not Settings(app_env="staging").docs_enabled
    assert Settings(app_env="development").docs_enabled


def check_cors_parsing() -> None:
    from core.config import Settings

    parsed = Settings(
        cors_origins="https://a.example.com, https://b.example.com ,"
    ).cors_origins_list
    # Trimmed, and the trailing empty segment dropped -- an empty origin would
    # never match anything and only makes the list look longer than it is.
    assert parsed == ["https://a.example.com", "https://b.example.com"]


def run() -> None:
    check_environment_parsing()
    check_development_is_left_alone()
    check_published_defaults_are_refused()
    check_weak_secret_is_refused()
    check_infrastructure_problems_are_refused()
    check_all_problems_reported_at_once()
    check_docs_are_hidden_when_hardened()
    check_cors_parsing()

    print("ENVIRONMENT SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
