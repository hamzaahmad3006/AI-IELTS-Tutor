/**
 * Device dimensions and fixed layout sizes.
 */

import { Dimensions } from 'react-native';

const window = Dimensions.get('window');

export const SCREEN = {
  width: window.width,
  height: window.height,
  isSmall: window.width < 360,
} as const;

export const LAYOUT = {
  headerHeight: 56,
  tabBarHeight: 64,
  buttonHeight: 52,
  inputHeight: 52,
  moduleTileHeight: 148,
  bandRingSize: 120,
  logoSizeSplash: 96,
  fabSize: 56,
  voiceControlSize: 96,
  hitSlop: 8,
} as const;
