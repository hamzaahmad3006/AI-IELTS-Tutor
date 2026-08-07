"""Per-environment behaviour, and a startup check that refuses unsafe production.

`APP_ENV` existed as a string nobody read, so every environment ran with
development defaults: a published JWT secret, wildcard CORS with credentials
enabled, interactive docs open to the internet, and a seeded admin whose
password is in the repository.

Each of those is fine on a laptop and a serious problem in production, and none
of them announces itself. A deployment with `JWT_SECRET=change_me_in_production`
works perfectly -- right up until someone reads the source, signs their own
token, and is an admin.

So the check runs at startup and refuses to boot rather than warning. A warning
in a log nobody reads is how these ship. The one thing worse than a service that
will not start is a service that starts insecure and looks fine.
"""

from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def parse(cls, raw: str) -> Environment:
        """Map a configured string onto an environment.

        An unrecognised value resolves to production, not development.
        A typo -- "prodcution" -- must not silently unlock the permissive path;
        the failure should be a service that refuses to start with weak config,
        not one that quietly runs with it.
        """
        try:
            return cls(raw.strip().lower())
        except ValueError:
            return cls.PRODUCTION

    @property
    def is_production(self) -> bool:
        return self is Environment.PRODUCTION

    @property
    def is_hardened(self) -> bool:
        """Staging is held to production's rules.

        A staging environment with production's weaknesses tests nothing about
        production, and it usually holds real data copied from it.
        """
        return self in (Environment.STAGING, Environment.PRODUCTION)


#: Values that ship in the repository. Any of these in a hardened environment
#: means the deployment is running on defaults someone can look up.
PUBLISHED_DEFAULTS = {
    "jwt_secret": "change_me_in_production",
    "seed_admin_password": "AdminPass123",
    "livekit_api_key": "devkey",
    "livekit_api_secret": "secret",
}

#: Shorter than this and a signing key is brute-forceable regardless of how
#: random it looks.
MIN_SECRET_LENGTH = 32


class UnsafeConfiguration(RuntimeError):
    """Configuration that must not be allowed to serve traffic."""


def audit(settings: object) -> list[str]:
    """Return every reason this configuration is unsafe for its environment.

    Returns all of them rather than the first, so a deployment is fixed in one
    pass instead of discovering the next problem on each restart.
    """
    env = Environment.parse(getattr(settings, "app_env", "development"))
    if not env.is_hardened:
        return []

    problems: list[str] = []

    for field, published in PUBLISHED_DEFAULTS.items():
        value = getattr(settings, field, None)
        if value and value == published:
            problems.append(
                f"{field.upper()} is still the value published in the "
                f"repository. Generate a real one."
            )

    secret = getattr(settings, "jwt_secret", "") or ""
    if secret and secret not in PUBLISHED_DEFAULTS.values():
        if len(secret) < MIN_SECRET_LENGTH:
            problems.append(
                f"JWT_SECRET is {len(secret)} characters; use at least "
                f"{MIN_SECRET_LENGTH}."
            )

    if getattr(settings, "is_sqlite", False):
        # SQLite in production means one file, one process, no concurrent
        # writers and no backups worth the name.
        problems.append(
            "DATABASE_URL points at SQLite. Use PostgreSQL outside development."
        )

    origins = list(getattr(settings, "cors_origins_list", []) or [])
    if "*" in origins:
        # A wildcard origin with credentials enabled is rejected by browsers
        # anyway, so this is both a security hole and a broken configuration.
        problems.append(
            "CORS_ORIGINS is '*'. List the origins that may call this API."
        )

    if not getattr(settings, "rate_limit_enabled", True):
        problems.append("RATE_LIMIT_ENABLED is false; login is unprotected.")

    return problems


def enforce(settings: object) -> None:
    """Raise unless this configuration is safe to serve traffic."""
    problems = audit(settings)
    if problems:
        listed = "\n  - ".join(problems)
        raise UnsafeConfiguration(
            "Refusing to start: this configuration is not safe for "
            f"{getattr(settings, 'app_env', 'this environment')}.\n"
            f"  - {listed}\n"
            "Set APP_ENV=development to run with development defaults."
        )
