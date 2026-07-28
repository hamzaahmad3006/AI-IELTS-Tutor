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
 *
 * Set to false to develop against the real API (see backend/README.md to start
 * it). This only applies in development — see `useMock` below.
 */
const USE_MOCK_IN_DEV = true;

/**
 * Mock data must never reach a release build: shipping fixtures would show
 * every user the same invented bands and feedback. `__DEV__` is false in
 * release bundles, so mocks are impossible there regardless of the flag above.
 */
const useMock = __DEV__ && USE_MOCK_IN_DEV;

export const API_CONFIG = {
  baseUrl: API_BASE_URL ?? `http://${DEV_HOST}:${DEV_PORT}/v1`,
  timeoutMs: 30000,
  version: 'v1',
  useMock,
} as const;
