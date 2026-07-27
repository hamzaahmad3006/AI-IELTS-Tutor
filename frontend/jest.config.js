/**
 * Jest configuration.
 *
 * `@react-native/jest-preset` was referenced but never installed, so `npm test`
 * failed to start. It is now a devDependency.
 */
module.exports = {
  preset: '@react-native/jest-preset',
  setupFiles: ['<rootDir>/jest.setup.js'],
  // These packages publish untranspiled ESM, so Babel must process them.
  transformIgnorePatterns: [
    'node_modules/(?!(@react-native|react-native|@react-navigation|react-redux|redux-persist|redux|immer|reselect|@reduxjs/toolkit|react-native-.*)/)',
  ],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
};
