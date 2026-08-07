/**
 * Types for values inlined from .env by react-native-dotenv.
 *
 * Every entry is optional. A fresh clone has no .env, and every consumer must
 * fall back to a default rather than crash on startup — a missing config file
 * should not be the difference between an app that runs and one that does not.
 *
 * Nothing secret belongs here. These values are inlined into the bundle at
 * build time, so anything listed ships inside the APK where it can be read.
 */
declare module '@env' {
  /** Full API base URL, overriding the platform default. */
  export const API_BASE_URL: string | undefined;
  /** Host for the dev backend, e.g. your machine's LAN IP for a real device. */
  export const API_HOST: string | undefined;
  export const API_PORT: string | undefined;
  /** 'true' serves local fixtures instead of calling the backend, in dev only. */
  export const USE_MOCK: string | undefined;
  /** LiveKit signalling URL the phone should connect to. */
  export const LIVEKIT_URL: string | undefined;
}
