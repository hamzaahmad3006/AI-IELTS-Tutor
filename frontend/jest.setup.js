/**
 * Jest setup: mock native modules that have no JS implementation under test.
 */

/* eslint-env jest */

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(() => Promise.resolve(null)),
  setItem: jest.fn(() => Promise.resolve()),
  removeItem: jest.fn(() => Promise.resolve()),
}));

jest.mock('react-native-linear-gradient', () => 'LinearGradient');

jest.mock('react-native-gesture-handler', () => ({
  GestureHandlerRootView: 'GestureHandlerRootView',
}));

// react-native-keychain is a native module with no JS fallback. The mock is an
// in-memory keychain rather than a set of jest.fn() stubs, so tests exercise
// real round-trip behaviour -- write then read must return what was written,
// which is the property that matters and the one a stub cannot check.
jest.mock('react-native-keychain', () => {
  const store = new Map();
  return {
    __store: store,
    ACCESSIBLE: {
      WHEN_UNLOCKED_THIS_DEVICE_ONLY: 'AccessibleWhenUnlockedThisDeviceOnly',
    },
    SECURITY_LEVEL: { SECURE_HARDWARE: 'SECURE_HARDWARE' },
    getSecurityLevel: jest.fn(() => Promise.resolve('SECURE_HARDWARE')),
    setGenericPassword: jest.fn((username, password, options) => {
      store.set(options.service, { username, password });
      return Promise.resolve(true);
    }),
    getGenericPassword: jest.fn(options =>
      Promise.resolve(store.get(options.service) ?? false),
    ),
    resetGenericPassword: jest.fn(options => {
      store.delete(options.service);
      return Promise.resolve(true);
    }),
  };
});

// The audio recorder is a Nitro native module with no JS fallback. Mocked as a
// small state machine rather than bare jest.fn()s so tests exercise real
// lifecycle behaviour -- starting twice, stopping when idle -- which is where
// the wrapper's logic actually lives.
jest.mock('react-native-audio-recorder-player', () => {
  let recording = false;
  return {
    __esModule: true,
    default: {
      startRecorder: jest.fn(() => {
        recording = true;
        return Promise.resolve('/data/user/0/app/cache/sound.m4a');
      }),
      stopRecorder: jest.fn(() => {
        if (!recording) {
          return Promise.reject(new Error('Recorder is not running'));
        }
        recording = false;
        return Promise.resolve('/data/user/0/app/cache/sound.m4a');
      }),
      addRecordBackListener: jest.fn(),
      removeRecordBackListener: jest.fn(),
      __reset: () => {
        recording = false;
      },
    },
  };
});
