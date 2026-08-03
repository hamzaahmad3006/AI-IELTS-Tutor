/**
 * API configuration.
 *
 * In development the API host is derived from the Metro dev-server URL, so the
 * same build works on an emulator and on a physical phone with no code edits:
 *   - emulator   -> Metro is 10.0.2.2 (Android) / localhost (iOS)
 *   - real phone -> Metro is the development machine's LAN IP (192.168.x.x)
 *
 * The phone must be on the same Wi-Fi network as the machine running the
 * backend, and the backend must listen on all interfaces:
 *     uvicorn main:app --host 0.0.0.0 --port 8000
 */

import { NativeModules, Platform } from 'react-native';

const DEV_PORT = 8000;

/** Fallback host per platform when the Metro URL cannot be read. */
const FALLBACK_HOST = Platform.select({
  android: '10.0.2.2', // Android emulator's alias for the host machine
  ios: 'localhost',
  default: 'localhost',
});

const hostFromUrl = (url: string | undefined): string | null => {
  if (typeof url !== 'string') {
    return null;
  }
  // e.g. http://192.168.18.61:8081/index.bundle?platform=android -> 192.168.18.61
  const match = url.match(/^https?:\/\/([^/:]+)(?::\d+)?/);
  return match ? match[1] : null;
};

/**
 * Host of the Metro dev server (i.e. the development machine) — exactly the
 * address the device has already proven it can reach.
 *
 * `getDevServer()` is used first because `NativeModules.SourceCode` is not
 * exposed under the New Architecture (Fabric); relying on it alone silently
 * fell back to the emulator alias and broke physical devices.
 */
const metroHost = (): string | null => {
  try {
    // No top-level export exists for this; see the Fabric note above.
    // A block disable rather than disable-next-line: Prettier reflows this
    // statement, which silently moves the violation off the targeted line.
    /* eslint-disable @react-native/no-deep-imports */
    const getDevServer =
      require('react-native/Libraries/Core/Devtools/getDevServer') as
        | (() => { url?: string })
        | { default?: () => { url?: string } };
    /* eslint-enable @react-native/no-deep-imports */
    const fn =
      typeof getDevServer === 'function' ? getDevServer : getDevServer.default;
    const host = hostFromUrl(fn?.().url);
    if (host) {
      return host;
    }
  } catch {
    // Not available (e.g. release build or test runner) - fall through.
  }
  return hostFromUrl(
    (NativeModules as { SourceCode?: { scriptURL?: string } }).SourceCode
      ?.scriptURL,
  );
};

const devHost = (): string => metroHost() ?? FALLBACK_HOST;

/**
 * Set this to target a deployed environment, e.g.
 *   const API_BASE_URL = 'https://api.aitutor.app/v1';
 * Leave null in development to use the auto-detected host above.
 */
const API_BASE_URL: string | null = null;

/**
 * Serve typed local fixtures instead of calling the backend.
 *
 * Set to false to develop against the real API (see backend/README.md to start
 * it). This only applies in development — see `useMock` below.
 */
const USE_MOCK_IN_DEV = false;

/**
 * Unit tests always use fixtures - there is no backend in the test runner.
 * `process` is provided by Jest/Node but is not in React Native's type set,
 * so it is read defensively rather than pulling in @types/node.
 */
const isTest =
  (globalThis as { process?: { env?: { NODE_ENV?: string } } }).process?.env
    ?.NODE_ENV === 'test';

/**
 * Mock data must never reach a release build: shipping fixtures would show
 * every user the same invented bands and feedback. `__DEV__` is false in
 * release bundles, so mocks are impossible there regardless of the flags above.
 */
const useMock = __DEV__ && (USE_MOCK_IN_DEV || isTest);

export const API_CONFIG = {
  baseUrl: API_BASE_URL ?? `http://${devHost()}:${DEV_PORT}/v1`,
  timeoutMs: 30000,
  version: 'v1',
  useMock,
} as const;

if (__DEV__ && !isTest) {
  // Surfaces the resolved backend address in Metro/logcat, which is the first
  // thing to check when a device reports "Network Error".
  console.log(
    `[api] baseUrl=${API_CONFIG.baseUrl} useMock=${API_CONFIG.useMock}`,
  );
}
