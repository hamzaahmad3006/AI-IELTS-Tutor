/**
 * Detox configuration.
 *
 * Android only, matching the project's scope.
 *
 * The AVD name is read from the environment rather than hardcoded, because
 * every developer's emulator is named differently and a hardcoded name means
 * the config only works on the machine it was written on.
 */

/** @type {Detox.DetoxConfig} */
module.exports = {
  testRunner: {
    args: {
      $0: 'jest',
      config: 'e2e/jest.config.js',
    },
    // A failing E2E run is usually one broken thing cascading, and the first
    // failure is the informative one. Bailing keeps the log readable.
    jest: { setupTimeout: 180_000 },
  },
  apps: {
    'android.debug': {
      type: 'android.apk',
      binaryPath: 'android/app/build/outputs/apk/debug/app-debug.apk',
      build:
        'cd android && gradlew.bat assembleDebug assembleAndroidTest -DtestBuildType=debug',
      reversePorts: [8081],
    },
    'android.release': {
      type: 'android.apk',
      binaryPath: 'android/app/build/outputs/apk/release/app-release.apk',
      build:
        'cd android && gradlew.bat assembleRelease assembleAndroidTest -DtestBuildType=release',
    },
  },
  devices: {
    emulator: {
      type: 'android.emulator',
      device: {
        // Set DETOX_AVD_NAME to your own AVD. `emulator -list-avds` shows them.
        avdName: process.env.DETOX_AVD_NAME || 'ielts_test',
      },
    },
    attached: {
      type: 'android.attached',
      // A real phone over ADB. This is the configuration that actually works
      // on this project right now: the emulator has never booted here.
      device: { adbName: process.env.DETOX_ADB_NAME || '.*' },
    },
  },
  configurations: {
    'android.emu.debug': {
      device: 'emulator',
      app: 'android.debug',
    },
    'android.attached.debug': {
      device: 'attached',
      app: 'android.debug',
    },
    'android.emu.release': {
      device: 'emulator',
      app: 'android.release',
    },
  },
};
