/**
 * Stand-in for the `@env` module under test.
 *
 * Every value is undefined on purpose, so tests exercise the fallback path —
 * which is what a fresh clone with no .env file actually runs.
 */

export const API_BASE_URL: string | undefined = undefined;
export const API_HOST: string | undefined = undefined;
export const API_PORT: string | undefined = undefined;
export const USE_MOCK: string | undefined = undefined;
export const LIVEKIT_URL: string | undefined = undefined;
