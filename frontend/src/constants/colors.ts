/**
 * Application color palette.
 *
 * Derived from the Stitch "Lumina IELTS / Illuminated Mastery" design system.
 * Every color used in the app MUST come from here — never hardcode hex values
 * inside screens or components.
 */

/** Raw brand palette (theme-independent primitives). */
export const PALETTE = {
  // Brand
  indigo: '#4F46E5',
  indigoDark: '#4338CA',
  indigoDeep: '#3525CD',
  indigoTint: '#4D44E3',
  indigoContainer: '#E2DFFF',
  indigoOnContainer: '#0F0069',

  // Accent (CTA / success momentum)
  teal: '#14B8A6',
  teal400: '#2DD4BF',
  teal600: '#0D9488',
  tealDeep: '#006B5F',
  tealContainer: '#6DF5E1',

  // Highlight (streaks / gamification / alerts)
  coral: '#FB7185',
  coralSoft: '#FFB2B9',

  // Neutrals
  ink: '#0F172A',
  ink2: '#131B2E',
  slate: '#334155',
  slate2: '#464555',
  slateMuted: '#64748B',
  outline: '#777587',
  outlineVariant: '#C7C4D8',
  cloud: '#F1F5F9',
  cloud2: '#F2F3FF',
  white: '#FFFFFF',
  black: '#000000',

  // Dark surfaces (deep navy-tinted, not pure black)
  navy0: '#0B1220',
  navy1: '#111827',
  navy2: '#1E293B',
  navyInverseOn: '#EEF0FF',

  // Semantic
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
  errorStrong: '#BA1A1A',
  info: '#3B82F6',
} as const;

/**
 * IELTS band-score scale colors.
 * These are functional/semantic — always applied to BandBadge, progress rings
 * and score charts to give instant visual feedback on performance.
 */
export const BAND_SCALE = {
  low: '#EF4444', // 0 - 4.5   (red)
  mid: '#F59E0B', // 5 - 6      (amber)
  high: '#84CC16', // 6.5 - 7    (lime)
  top: '#10B981', // 7.5 - 9    (green)
} as const;

/** Light theme semantic colors. */
export const LIGHT_COLORS = {
  // Surfaces / backgrounds
  background: '#FAF8FF',
  surface: '#FAF8FF',
  surfaceDim: '#D2D9F4',
  surfaceBright: '#FAF8FF',
  card: '#FFFFFF',
  cardAlt: '#F2F3FF',
  container: '#EAEDFF',
  containerHigh: '#E2E7FF',
  containerHighest: '#DAE2FD',

  // Text / content
  onSurface: '#131B2E',
  onSurfaceVariant: '#464555',
  textPrimary: '#131B2E',
  textSecondary: '#464555',
  textMuted: '#777587',
  textInverse: '#FFFFFF',

  // Brand roles
  primary: PALETTE.indigo,
  primaryDeep: PALETTE.indigoDeep,
  onPrimary: '#FFFFFF',
  primaryContainer: PALETTE.indigoContainer,
  onPrimaryContainer: PALETTE.indigoOnContainer,

  accent: PALETTE.teal,
  accentGradientStart: PALETTE.teal400,
  accentGradientEnd: PALETTE.teal600,
  onAccent: '#FFFFFF',

  highlight: PALETTE.coral,

  // Lines / dividers
  outline: PALETTE.outline,
  outlineVariant: PALETTE.outlineVariant,
  border: '#E2E7FF',

  // Semantic
  success: PALETTE.success,
  warning: PALETTE.warning,
  error: PALETTE.error,
  info: PALETTE.info,

  // Feedback highlight backgrounds (transcript / essay markers)
  errorHighlight: '#FFDAD6',
  suggestionHighlight: '#DAD7FF',
  strongHighlight: '#E2DFFF',

  // Shadow
  shadow: 'rgba(79, 70, 229, 0.15)',
} as const;

/** Dark theme semantic colors. */
export const DARK_COLORS = {
  background: PALETTE.navy0,
  surface: PALETTE.navy0,
  surfaceDim: '#0A0F1A',
  surfaceBright: PALETTE.navy2,
  card: PALETTE.navy1,
  cardAlt: '#182131',
  container: PALETTE.navy2,
  containerHigh: '#233047',
  containerHighest: '#2A3A55',

  onSurface: '#EEF0FF',
  onSurfaceVariant: '#C7C4D8',
  textPrimary: '#EEF0FF',
  textSecondary: '#C7C4D8',
  textMuted: '#8B90A8',
  textInverse: '#131B2E',

  primary: '#C3C0FF',
  primaryDeep: PALETTE.indigo,
  onPrimary: '#131B2E',
  primaryContainer: '#3323CC',
  onPrimaryContainer: '#DAD7FF',

  accent: PALETTE.teal,
  accentGradientStart: PALETTE.teal400,
  accentGradientEnd: PALETTE.teal600,
  onAccent: '#00201C',

  highlight: PALETTE.coral,

  outline: '#8B90A8',
  outlineVariant: '#3A4560',
  border: '#233047',

  success: PALETTE.success,
  warning: PALETTE.warning,
  error: '#FFB4AB',
  info: PALETTE.info,

  errorHighlight: '#93000A',
  suggestionHighlight: '#3323CC',
  strongHighlight: '#2A2470',

  shadow: 'rgba(0, 0, 0, 0.5)',
} as const;

/**
 * Resolve the band-scale color for a given IELTS band (0–9, 0.5 steps).
 */
export const getBandColor = (band: number): string => {
  if (band <= 4.5) {
    return BAND_SCALE.low;
  }
  if (band <= 6) {
    return BAND_SCALE.mid;
  }
  if (band <= 7) {
    return BAND_SCALE.high;
  }
  return BAND_SCALE.top;
};

/**
 * Human-readable band-scale label (used on BandBadge, e.g. "LIME").
 */
export const getBandScaleLabel = (band: number): string => {
  if (band <= 4.5) {
    return 'RED';
  }
  if (band <= 6) {
    return 'AMBER';
  }
  if (band <= 7) {
    return 'LIME';
  }
  return 'GREEN';
};
