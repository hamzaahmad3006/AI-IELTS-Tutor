/**
 * React Native CLI config.
 * Add Plus Jakarta Sans + Inter .ttf files to src/assets/fonts, then run:
 *   npx react-native-asset
 * to link the custom fonts referenced in src/constants/typography.ts.
 */
module.exports = {
  project: {
    ios: {},
    android: {},
  },
  assets: ['./src/assets/fonts/'],
};
