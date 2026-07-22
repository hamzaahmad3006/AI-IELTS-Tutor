/**
 * Composed theme objects (light + dark). Consumed via the ThemeProvider /
 * useTheme hook so components never import raw color maps directly.
 */

import { LIGHT_COLORS, DARK_COLORS } from './colors';
import { TYPOGRAPHY } from './typography';
import { SPACING, RADIUS } from './spacing';
import { SHADOWS } from './shadows';

/** Structural color contract shared by light + dark themes. */
export type ThemeColors = { readonly [K in keyof typeof LIGHT_COLORS]: string };
export type ThemeMode = 'light' | 'dark';

export interface Theme {
  mode: ThemeMode;
  colors: ThemeColors;
  typography: typeof TYPOGRAPHY;
  spacing: typeof SPACING;
  radius: typeof RADIUS;
  shadows: typeof SHADOWS;
}

export const lightTheme: Theme = {
  mode: 'light',
  colors: LIGHT_COLORS,
  typography: TYPOGRAPHY,
  spacing: SPACING,
  radius: RADIUS,
  shadows: SHADOWS,
};

export const darkTheme: Theme = {
  mode: 'dark',
  // DARK_COLORS is structurally identical to LIGHT_COLORS (same keys).
  colors: DARK_COLORS,
  typography: TYPOGRAPHY,
  spacing: SPACING,
  radius: RADIUS,
  shadows: SHADOWS,
};

export const getTheme = (mode: ThemeMode): Theme =>
  mode === 'dark' ? darkTheme : lightTheme;
