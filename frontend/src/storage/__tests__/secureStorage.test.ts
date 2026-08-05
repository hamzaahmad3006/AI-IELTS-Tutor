/**
 * Tests for the Keystore-backed persist engine.
 *
 * The behaviour worth pinning is what happens when the Keystore fails, because
 * the tempting implementations are all wrong in the same direction: they keep
 * the user logged in by quietly writing the credential somewhere weaker.
 */

import * as Keychain from 'react-native-keychain';
import {
  isSecureStorageAvailable,
  secureStorage,
  setSecureStorageReporter,
} from '../secureStorage';
import type { SecureStorageEvent } from '../secureStorage';

const mocked = Keychain as unknown as {
  __store: Map<string, unknown>;
  getSecurityLevel: jest.Mock;
  setGenericPassword: jest.Mock;
  getGenericPassword: jest.Mock;
  resetGenericPassword: jest.Mock;
};

describe('secureStorage', () => {
  beforeEach(() => {
    mocked.__store.clear();
    jest.clearAllMocks();
    setSecureStorageReporter(undefined);
  });

  it('round-trips a value', async () => {
    await secureStorage.setItem('auth', '{"token":"abc"}');
    await expect(secureStorage.getItem('auth')).resolves.toBe(
      '{"token":"abc"}',
    );
  });

  it('returns null for a key that was never written', async () => {
    await expect(secureStorage.getItem('auth')).resolves.toBeNull();
  });

  it('namespaces keys so two slices cannot collide', async () => {
    await secureStorage.setItem('auth', 'one');
    await secureStorage.setItem('other', 'two');

    await expect(secureStorage.getItem('auth')).resolves.toBe('one');
    await expect(secureStorage.getItem('other')).resolves.toBe('two');

    const services = [...mocked.__store.keys()] as string[];
    expect(services).toHaveLength(2);
    // Distinct entries, each namespaced and ending in its own key -- a shared
    // service name would make the second write overwrite the first.
    expect(new Set(services).size).toBe(2);
    services.forEach(service =>
      expect(service).toMatch(/^com\.aiieltstutor\.persist\.(auth|other)$/),
    );
  });

  it('removes a value', async () => {
    await secureStorage.setItem('auth', 'x');
    await secureStorage.removeItem('auth');
    await expect(secureStorage.getItem('auth')).resolves.toBeNull();
  });

  it('writes at rest only while the device is unlocked', async () => {
    await secureStorage.setItem('auth', 'x');
    const options = mocked.setGenericPassword.mock.calls[0][2];
    expect(options.accessible).toBe(
      Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    );
  });

  describe('when the Keystore fails', () => {
    it('rethrows a failed write instead of degrading to plaintext', async () => {
      const boom = new Error('keystore unavailable');
      mocked.setGenericPassword.mockRejectedValueOnce(boom);

      // The critical assertion. Falling back to AsyncStorage here would keep
      // the user logged in and silently store a live credential in the clear.
      await expect(secureStorage.setItem('auth', 'secret')).rejects.toThrow(
        boom,
      );
      expect(mocked.__store.size).toBe(0);
    });

    it('reports a failed write', async () => {
      const events: SecureStorageEvent[] = [];
      setSecureStorageReporter(e => events.push(e));
      mocked.setGenericPassword.mockRejectedValueOnce(new Error('nope'));

      await expect(secureStorage.setItem('auth', 'secret')).rejects.toThrow();
      expect(events).toHaveLength(1);
      expect(events[0].type).toBe('write-failed');
      expect(events[0].key).toBe('auth');
    });

    it('returns null on a failed read rather than throwing', async () => {
      // redux-persist treats a throw from getItem as fatal, so the app would
      // not start at all. Null rehydrates to the initial state: logged out,
      // which is recoverable by logging in again.
      mocked.getGenericPassword.mockRejectedValueOnce(new Error('nope'));
      await expect(secureStorage.getItem('auth')).resolves.toBeNull();
    });

    it('reports a failed read', async () => {
      const events: SecureStorageEvent[] = [];
      setSecureStorageReporter(e => events.push(e));
      mocked.getGenericPassword.mockRejectedValueOnce(new Error('nope'));

      await secureStorage.getItem('auth');
      expect(events[0].type).toBe('read-failed');
    });

    it('does not throw when logout cannot clear the entry', async () => {
      // Logout must complete regardless: the in-memory state is cleared either
      // way, so refusing to finish would leave the UI in a signed-in state.
      const events: SecureStorageEvent[] = [];
      setSecureStorageReporter(e => events.push(e));
      mocked.resetGenericPassword.mockRejectedValueOnce(new Error('nope'));

      await expect(secureStorage.removeItem('auth')).resolves.toBeUndefined();
      expect(events[0].type).toBe('write-failed');
    });
  });

  describe('availability', () => {
    it('is available when the device reports a security level', async () => {
      await expect(isSecureStorageAvailable()).resolves.toBe(true);
    });

    it('is unavailable when the probe throws', async () => {
      mocked.getSecurityLevel.mockRejectedValueOnce(new Error('no keystore'));
      await expect(isSecureStorageAvailable()).resolves.toBe(false);
    });

    it('is unavailable when the device reports no security level', async () => {
      mocked.getSecurityLevel.mockResolvedValueOnce(null);
      await expect(isSecureStorageAvailable()).resolves.toBe(false);
    });

    it('probes without writing anything', async () => {
      await isSecureStorageAvailable();
      expect(mocked.setGenericPassword).not.toHaveBeenCalled();
      expect(mocked.__store.size).toBe(0);
    });
  });
});
