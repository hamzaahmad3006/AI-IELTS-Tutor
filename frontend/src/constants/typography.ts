/**
 * Typography system.
 *
 * Pairs Plus Jakarta Sans (headings — modern, friendly geometry) with
 * Inter (body — utilitarian precision).
 *
 * NOTE: the font .ttf files must be placed in `src/assets/fonts` and linked
 * via `react-native.config.js` + `npx react-native-asset`. Until linked, RN
 * will fall back to the system font, so the app still runs.
 */

import type { TextStyle } from 'react-native';

export const FONT_FAMILY = {
  headingExtraBold: 'PlusJakartaSans-ExtraBold',
  headingBold: 'PlusJakartaSans-Bold',
  headingSemiBold: 'PlusJakartaSans-SemiBold',
  bodyRegular: 'Inter-Regular',
  bodyMedium: 'Inter-Medium',
  bodySemiBold: 'Inter-SemiBold',
  bodyBold: 'Inter-Bold',
} as const;

export const FONT_SIZE = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 18,
  xl: 20,
  xxl: 24,
  display: 28,
  displayLg: 32,
  hero: 48,
} as const;

export const FONT_WEIGHT = {
  regular: '400',
  medium: '500',
  semiBold: '600',
  bold: '700',
  extraBold: '800',
} as const satisfies Record<string, TextStyle['fontWeight']>;

/**
 * Named typography presets. Screens should reference these via the `variant`
 * prop of the shared <AppText /> component instead of styling text ad hoc.
 */
export const TYPOGRAPHY = {
  displayLg: {
    fontFamily: FONT_FAMILY.headingExtraBold,
    fontSize: FONT_SIZE.hero,
    fontWeight: FONT_WEIGHT.extraBold,
    lineHeight: 52,
    letterSpacing: -1,
  },
  headlineLg: {
    fontFamily: FONT_FAMILY.headingBold,
    fontSize: FONT_SIZE.displayLg,
    fontWeight: FONT_WEIGHT.bold,
    lineHeight: 38,
  },
  headlineMobile: {
    fontFamily: FONT_FAMILY.headingBold,
    fontSize: FONT_SIZE.display,
    fontWeight: FONT_WEIGHT.bold,
    lineHeight: 34,
  },
  headlineMd: {
    fontFamily: FONT_FAMILY.headingBold,
    fontSize: FONT_SIZE.xxl,
    fontWeight: FONT_WEIGHT.bold,
    lineHeight: 31,
  },
  titleLg: {
    fontFamily: FONT_FAMILY.headingSemiBold,
    fontSize: FONT_SIZE.xl,
    fontWeight: FONT_WEIGHT.semiBold,
    lineHeight: 28,
  },
  bodyLg: {
    fontFamily: FONT_FAMILY.bodyRegular,
    fontSize: FONT_SIZE.lg,
    fontWeight: FONT_WEIGHT.regular,
    lineHeight: 29,
  },
  bodyMd: {
    fontFamily: FONT_FAMILY.bodyRegular,
    fontSize: FONT_SIZE.md,
    fontWeight: FONT_WEIGHT.regular,
    lineHeight: 26,
  },
  bodySm: {
    fontFamily: FONT_FAMILY.bodyRegular,
    fontSize: FONT_SIZE.sm,
    fontWeight: FONT_WEIGHT.regular,
    lineHeight: 22,
  },
  labelMd: {
    fontFamily: FONT_FAMILY.bodySemiBold,
    fontSize: FONT_SIZE.sm,
    fontWeight: FONT_WEIGHT.semiBold,
    lineHeight: 14,
    letterSpacing: 0.3,
  },
  labelSm: {
    fontFamily: FONT_FAMILY.bodyMedium,
    fontSize: FONT_SIZE.xs,
    fontWeight: FONT_WEIGHT.medium,
    lineHeight: 12,
    letterSpacing: 0.2,
  },
  button: {
    fontFamily: FONT_FAMILY.bodySemiBold,
    fontSize: FONT_SIZE.md,
    fontWeight: FONT_WEIGHT.semiBold,
    lineHeight: 20,
  },
} as const satisfies Record<string, TextStyle>;

export type TypographyVariant = keyof typeof TYPOGRAPHY;
