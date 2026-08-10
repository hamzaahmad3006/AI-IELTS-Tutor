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

  // Deep semantic variants, for semantic colour used as TEXT on a light
  // surface. The bright versions above are tuned for dark surfaces and for
  // fills; as text on white they run 2.15:1 to 3.76:1, under the 4.5:1 WCAG AA
  // asks of body text. Not academic here — these carry form validation errors
  // and the consent warning, the words a user can least afford to miss. Fills,
  // icons and the band scale keep the bright versions, which clear the 3:1
  // that non-text content needs.
  successDeep: '#065F46',
  warningDeep: '#92400E',
  errorDeep: '#B91C1C',
  infoDeep: '#1D4ED8',

  // Ink for use on the teal accent. White on teal is 1.86:1 at the light end
  // of the accent gradient — that is the primary CTA's own label. Near-black
  // with a teal cast keeps the gradient the design intends and makes the label
  // readable; the dark theme already made this exact choice.
  onTeal: '#00201C',

  // Muted text, one step darker than `outline`. They were the same value, but
  // a divider needs 3:1 and body text needs 4.5:1, so one value cannot serve
  // both roles.
  mutedText: '#605E70',
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

/**
 * Foreground for text drawn on a bright, theme-independent fill — band pills,
 * vocabulary grade buttons, any saturated swatch that stays the same colour in
 * both themes.
 *
 * Fixed rather than themed, because the fill is fixed. Those places used
 * `textInverse`, which flips with the theme while the swatch underneath does
 * not, so the same amber pill got dark text in dark mode and white text in
 * light mode. The light one was 2.15:1; the lime band was 1.98:1 and the
 * "Hard" grade button 2.15:1.
 *
 * One dark ink serves all of them: 4.56:1 on the weakest (red), up to 8.69:1
 * on lime.
 */
export const ON_BRIGHT_FILL = '#131B2E';

/** Foreground for text on a dark, theme-independent fill (the indigo CTA). */
export const ON_DARK_FILL = '#FFFFFF';

/** Relative luminance, per WCAG 2.1. */
const relativeLuminance = (hex: string): number => {
  const channels = [1, 3, 5]
    .map(offset => parseInt(hex.substr(offset, 2), 16) / 255)
    .map(value =>
      value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4,
    );
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
};

const contrastRatio = (a: string, b: string): number => {
  const x = relativeLuminance(a);
  const y = relativeLuminance(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
};

/**
 * The readable foreground for a fill that does not follow the theme.
 *
 * Fixed fills are everywhere here — band pills, difficulty chips, the indigo
 * mock-test card, the teal checkboxes — and they were all using
 * `textInverse`, which means "white" in the light theme and "near-black" in
 * the dark one. Since the fill underneath does not flip, exactly one of the
 * two themes got it wrong every time: white on amber at 2.15:1 in light mode,
 * near-black on indigo at 2.70:1 in dark mode.
 *
 * Choosing by measurement rather than by theme fixes the whole class, and
 * keeps working when someone adds a colour.
 */
export const readableOn = (fill: string): string =>
  contrastRatio(ON_BRIGHT_FILL, fill) >= contrastRatio(ON_DARK_FILL, fill)
    ? ON_BRIGHT_FILL
    : ON_DARK_FILL;

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
  textMuted: PALETTE.mutedText,
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
  onAccent: PALETTE.onTeal,

  // Coach banners, tips and inline suggestion highlights. These were
  // `PALETTE.tealContainer` applied directly, which does not follow the theme
  // — so in dark mode a light mint panel kept near-white text on it, at
  // 1.17:1. A container needs its own foreground, and both need to move with
  // the theme.
  accentContainer: PALETTE.tealContainer,
  onAccentContainer: PALETTE.onTeal,

  highlight: PALETTE.coral,

  // Lines / dividers
  outline: PALETTE.outline,
  outlineVariant: PALETTE.outlineVariant,
  border: '#E2E7FF',

  // Semantic. Deep variants because these appear as text on light surfaces --
  // see the note in PALETTE. BAND_SCALE keeps the bright versions, since it is
  // read as a chart colour rather than as words.
  success: PALETTE.successDeep,
  warning: PALETTE.warningDeep,
  error: PALETTE.errorDeep,
  info: PALETTE.infoDeep,

  // Feedback highlight backgrounds (transcript / essay markers)
  errorHighlight: '#FFDAD6',
  suggestionHighlight: '#DAD7FF',
  strongHighlight: '#E2DFFF',

  // Shadow
  shadow: 'rgba(79, 70, 229, 0.15)',
  // Dimming layer behind modals and bottom sheets.
  scrim: 'rgba(19, 27, 46, 0.45)',
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
  // Lightened from #8B90A8, which read at 3.63:1 on the raised containers.
  // Muted is a tone, not a licence to fall under the readable threshold.
  textMuted: '#A2A7BE',
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

  // The mint/ink pair inverted: a deep teal panel carrying mint text, so the
  // banner reads as part of a dark screen instead of a light rectangle
  // punched into it.
  accentContainer: '#00504A',
  onAccentContainer: PALETTE.tealContainer,

  highlight: PALETTE.coral,

  outline: '#8B90A8',
  outlineVariant: '#3A4560',
  border: '#233047',

  success: PALETTE.success,
  warning: PALETTE.warning,
  error: '#FFB4AB',
  // The mid-blue that works on white is too dark against a raised dark
  // container (3.11:1). Dark themes need their accents lighter, not merely
  // reused.
  info: '#93C5FD',

  errorHighlight: '#93000A',
  suggestionHighlight: '#3323CC',
  strongHighlight: '#2A2470',

  shadow: 'rgba(0, 0, 0, 0.5)',
  scrim: 'rgba(0, 0, 0, 0.6)',
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
