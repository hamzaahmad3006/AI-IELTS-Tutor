/**
 * API configuration.
 *
 * Defaults are chosen so `npm run android` / `npm run ios` reach a backend
 * running on the development machine without editing code:
 *   - Android emulator reaches the host via 10.0.2.2
 *   - iOS simulator shares the host network, so localhost works
 *
 * To point at a physical device, staging or production, set API_BASE_URL below
 * (or wire it to an env loader such as react-native-config).
 */

import { Platform } from 'react-native';

/** Host that reaches the developer machine from each platform's emulator. */
const DEV_HOST = Platform.select({
  android: '10.0.2.2',
  ios: 'localhost',
  default: 'localhost',
});

const DEV_PORT = 8000;

/**
 * Override to target a real device or a deployed environment, e.g.
 *   const API_BASE_URL = 'http://192.168.1.42:8000/v1';   // physical device
 *   const API_BASE_URL = 'https://api.aitutor.app/v1';     // production
 */
const API_BASE_URL: string | null = null;

/**
 * Serve typed local fixtures instead of calling the backend.
 * Set to false to run against the real API (see backend/README.md to start it).
 */
const USE_MOCK = true;

export const API_CONFIG = {
  baseUrl: API_BASE_URL ?? `http://${DEV_HOST}:${DEV_PORT}/v1`,
  timeoutMs: 30000,
  version: 'v1',
  useMock: USE_MOCK,
} as const;
