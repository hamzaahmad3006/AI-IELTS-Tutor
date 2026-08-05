/**
 * redux-persist storage engine backed by the Android Keystore.
 *
 * Tokens were persisted through AsyncStorage, which on Android is an
 * app-private file with no encryption. That is adequate against another app on
 * a healthy device and inadequate against anything else: a rooted phone, an ADB
 * backup, or a stolen device with an unlocked bootloader all yield the file, and
 * the access token in it is a live credential.
 *
 * react-native-keychain stores the value under a hardware-backed key instead,
 * so the bytes on disk are useless without the device.
 *
 * The design decision that matters here is what happens when the Keystore is
 * unavailable -- an emulator without a lock screen, an OEM with a broken
 * implementation, a module that failed to link. The tempting fallback is
 * AsyncStorage, which keeps everyone logged in. It is the wrong one: it
 * silently downgrades every user to plaintext storage, and nobody finds out.
 * This engine fails the write instead, which logs the user out. Being logged
 * out is visible and recoverable; being quietly insecure is neither.
 */

import * as Keychain from 'react-native-keychain';

/** One Keychain entry per persist key, namespaced to avoid collisions. */
const SERVICE_PREFIX = 'com.aiieltstutor.persist.';

/** The username field is unused -- Keychain requires one, so it is a constant. */
const ACCOUNT = 'redux-persist';

const serviceFor = (key: string): string => `${SERVICE_PREFIX}${key}`;

export type SecureStorageEvent =
  | { type: 'unavailable'; key: string; error: unknown }
  | { type: 'write-failed'; key: string; error: unknown }
  | { type: 'read-failed'; key: string; error: unknown };

let listener: ((event: SecureStorageEvent) => void) | undefined;

/**
 * Register a reporter for secure-storage failures.
 *
 * These are exactly the failures that must not pass silently: every one of them
 * means a session did not survive, and the user is about to be logged out for
 * a reason they cannot see.
 */
export const setSecureStorageReporter = (
  fn: ((event: SecureStorageEvent) => void) | undefined,
): void => {
  listener = fn;
};

const report = (event: SecureStorageEvent): void => {
  listener?.(event);
};

/**
 * Whether the Keystore can actually be used on this device.
 *
 * Checked by asking the library what security level it supports rather than by
 * attempting a write, so the probe leaves nothing behind.
 */
export const isSecureStorageAvailable = async (): Promise<boolean> => {
  try {
    const level = await Keychain.getSecurityLevel();
    return level !== null && level !== undefined;
  } catch (error) {
    report({ type: 'unavailable', key: '<probe>', error });
    return false;
  }
};

export const secureStorage = {
  async getItem(key: string): Promise<string | null> {
    try {
      const entry = await Keychain.getGenericPassword({
        service: serviceFor(key),
      });
      // `false` means "no entry", which is a normal cold start, not a failure.
      return entry === false ? null : entry.password;
    } catch (error) {
      // A read failure is reported but returns null rather than throwing:
      // redux-persist treats a throw here as fatal and the app would not start
      // at all. A null rehydrates to the initial state, i.e. logged out.
      report({ type: 'read-failed', key, error });
      return null;
    }
  },

  async setItem(key: string, value: string): Promise<void> {
    try {
      await Keychain.setGenericPassword(ACCOUNT, value, {
        service: serviceFor(key),
        // Written when the device is unlocked, and readable afterwards without
        // a prompt. Requiring biometrics on every token refresh would put a
        // fingerprint prompt in the middle of ordinary API calls.
        accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
      });
    } catch (error) {
      report({ type: 'write-failed', key, error });
      // Rethrown deliberately. Swallowing it would leave the app looking
      // logged in until the next restart, then logged out with no explanation.
      throw error;
    }
  },

  async removeItem(key: string): Promise<void> {
    try {
      await Keychain.resetGenericPassword({ service: serviceFor(key) });
    } catch (error) {
      // A failed delete on logout is the one case worth being loud about, but
      // it must not prevent the rest of logout from completing -- the in-memory
      // state is cleared regardless, so the session ends either way.
      report({ type: 'write-failed', key, error });
    }
  },
};

export default secureStorage;
