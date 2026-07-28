/**
 * Guards the mock/real data switch.
 *
 * Shipping fixture data in a release build would show every user the same
 * invented band scores and feedback, so this is a correctness guarantee, not a
 * style preference.
 */

describe('API_CONFIG.useMock', () => {
  const loadConfig = (dev: boolean) => {
    jest.resetModules();
    // __DEV__ is a global injected by the React Native runtime.
    (globalThis as unknown as { __DEV__: boolean }).__DEV__ = dev;
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    return require('../config').API_CONFIG as { useMock: boolean; baseUrl: string };
  };

  const originalDev = (globalThis as unknown as { __DEV__: boolean }).__DEV__;

  afterEach(() => {
    (globalThis as unknown as { __DEV__: boolean }).__DEV__ = originalDev;
    jest.resetModules();
  });

  it('never uses mock data in a release build', () => {
    expect(loadConfig(false).useMock).toBe(false);
  });

  it('may use mock data in development', () => {
    // Development is allowed to use fixtures; the value follows USE_MOCK_IN_DEV.
    expect(typeof loadConfig(true).useMock).toBe('boolean');
  });

  it('always exposes a versioned base URL', () => {
    const config = loadConfig(false);
    expect(config.baseUrl).toMatch(/\/v1$/);
  });
});
