/**
 * Jest runner for Detox.
 *
 * Separate from the unit-test config on purpose: these run against a real
 * device, take minutes rather than milliseconds, and must never be picked up
 * by `npm test`. A unit run that tries to launch an emulator fails in a way
 * that looks like a broken test rather than a misconfiguration.
 */
module.exports = {
  rootDir: '..',
  testMatch: ['<rootDir>/e2e/**/*.e2e.js'],
  testTimeout: 240_000,
  maxWorkers: 1,
  globalSetup: 'detox/runners/jest/globalSetup',
  globalTeardown: 'detox/runners/jest/globalTeardown',
  reporters: ['detox/runners/jest/reporter'],
  testEnvironment: 'detox/runners/jest/testEnvironment',
  verbose: true,
};
