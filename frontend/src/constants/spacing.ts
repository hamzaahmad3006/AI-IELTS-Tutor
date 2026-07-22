/**
 * 8pt spacing grid + corner radii + z-index tokens.
 * Screens must use these instead of magic numbers.
 */

export const SPACING = {
  none: 0,
  xxs: 4,
  xs: 8,
  sm: 12,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
  // Layout-specific
  screenPadding: 16,
  screenPaddingDesktop: 32,
  gutter: 24,
  sectionGap: 32,
} as const;

export const RADIUS = {
  sm: 4,
  md: 8,
  input: 12,
  button: 12,
  card: 16,
  lg: 24,
  pill: 999,
} as const;

export const Z_INDEX = {
  base: 0,
  card: 1,
  header: 10,
  overlay: 100,
  modal: 1000,
  toast: 2000,
} as const;

export type SpacingToken = keyof typeof SPACING;
export type RadiusToken = keyof typeof RADIUS;
