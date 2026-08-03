/**
 * Jest configuration.
 *
 * `@react-native/jest-preset` was referenced but never installed, so `npm test`
 * failed to start. It is now a devDependency.
 */
module.exports = {
  preset: '@react-native/jest-preset',
  // Jest does not read Babel's module-resolver aliases, so they are mirrored
  // here. Out of sync, tests fail to resolve imports the app resolves fine.
  moduleNameMapper: {
    '^@api$': '<rootDir>/src/api',
    '^@api/(.*)$': '<rootDir>/src/api/$1',
    '^@components$': '<rootDir>/src/components',
    '^@components/(.*)$': '<rootDir>/src/components/$1',
    '^@constants$': '<rootDir>/src/constants',
    '^@constants/(.*)$': '<rootDir>/src/constants/$1',
    '^@navigation$': '<rootDir>/src/AppNavigation',
    '^@navigation/(.*)$': '<rootDir>/src/AppNavigation/$1',
    '^@redux$': '<rootDir>/src/redux',
    '^@redux/(.*)$': '<rootDir>/src/redux/$1',
    '^@screens/(.*)$': '<rootDir>/src/screens/$1',
    '^@assets$': '<rootDir>/src/assets',
    '^@models$': '<rootDir>/src/types',
    '^@models/(.*)$': '<rootDir>/src/types/$1',
  },
  setupFiles: ['<rootDir>/jest.setup.js'],
  // These packages publish untranspiled ESM, so Babel must process them.
  transformIgnorePatterns: [
    'node_modules/(?!(@react-native|react-native|@react-navigation|react-redux|redux-persist|redux|immer|reselect|@reduxjs/toolkit|react-native-.*)/)',
  ],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
};
