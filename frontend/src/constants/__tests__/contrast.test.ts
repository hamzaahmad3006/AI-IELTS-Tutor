/**
 * WCAG 2.1 AA contrast for every theme colour pair the app actually renders.
 *
 * This is the part of an accessibility audit that does not need a device: the
 * ratios are arithmetic on the palette, so they can be checked here and kept
 * from regressing, rather than re-eyeballed on a phone every release.
 *
 * It found eleven real failures. The worst was the coach banner at 1.17:1 --
 * near-white text on a mint panel that never followed the theme, so the text
 * was simply not there in dark mode. Then the primary CTA's own label at
 * 1.86:1, the LIME band badge at 1.98:1, and the consent warning at 2.15:1.
 *
 * All of them were invisible to every existing test, because nothing had ever
 * compared two colours to each other.
 *
 * Thresholds are the AA ones: 4.5:1 for body text, 3:1 for large text and for
 * non-text content like borders and icons.
 */

import {
  BAND_SCALE,
  DARK_COLORS,
  LIGHT_COLORS,
  ON_BRIGHT_FILL,
  ON_DARK_FILL,
  PALETTE,
  readableOn,
} from '../colors';

const AA_TEXT = 4.5;
const AA_LARGE_OR_NON_TEXT = 3.0;

/** Relative luminance, per WCAG 2.1 §relative-luminance. */
const luminance = (hex: string): number => {
  const match = /^#([0-9a-f]{6})$/i.exec(hex);
  if (!match) {
    throw new Error(`Not an opaque hex colour: ${hex}`);
  }
  const channels = [0, 2, 4]
    .map(offset => parseInt(match[1].substr(offset, 2), 16) / 255)
    .map(value =>
      value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4,
    );
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
};

const contrast = (foreground: string, background: string): number => {
  const a = luminance(foreground);
  const b = luminance(background);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
};

/**
 * Every surface a piece of text can land on. Text is not placed against one
 * background: a card sits on the page background, a chip sits on the card, so
 * a colour has to clear the whole set rather than the most flattering member
 * of it.
 */
const surfaceKeys = [
  'background',
  'surface',
  'card',
  'cardAlt',
  'container',
  'containerHigh',
  'containerHighest',
] as const;

/** Foreground roles that carry words, and so need the 4.5:1 bar. */
const textKeys = [
  'textPrimary',
  'textSecondary',
  'textMuted',
  'onSurface',
  'onSurfaceVariant',
  'primary',
  'success',
  'warning',
  'error',
  'info',
] as const;

/** Pairs where the name states the intent: "on X" must be readable on X. */
const onPairs: ReadonlyArray<readonly [string, string]> = [
  ['onPrimary', 'primary'],
  ['onPrimaryContainer', 'primaryContainer'],
  ['onAccent', 'accent'],
  ['textInverse', 'primary'],
];

const themes = [
  ['light', LIGHT_COLORS],
  ['dark', DARK_COLORS],
] as const;

describe.each(themes)('%s theme contrast', (_name, colors) => {
  it.each(textKeys)('%s is readable on every surface', textKey => {
    const foreground: string = colors[textKey];
    // Collected rather than asserted one at a time, so a failure lists every
    // bad surface with its ratio. Which surfaces fail, and by how much, is
    // what says whether to nudge the colour or rethink the pairing -- the
    // first failing pair alone does not.
    const failures = surfaceKeys
      .map(surfaceKey => ({
        pair: `${textKey} on ${surfaceKey}`,
        swatches: `${foreground} / ${colors[surfaceKey]}`,
        ratio: Number(contrast(foreground, colors[surfaceKey]).toFixed(2)),
      }))
      .filter(entry => entry.ratio < AA_TEXT);

    expect(failures).toEqual([]);
  });

  it.each(onPairs)('%s is readable on %s', (foregroundKey, backgroundKey) => {
    const foreground: string = colors[foregroundKey as keyof typeof colors];
    const background: string = colors[backgroundKey as keyof typeof colors];
    expect(contrast(foreground, background)).toBeGreaterThanOrEqual(AA_TEXT);
  });

  it('the primary CTA label is readable across the whole accent gradient', () => {
    // The button is a vertical gradient, so the label has to clear both ends.
    // Checking only the mid tone is what let 1.86:1 ship: the flat `accent`
    // token looked merely poor while the gradient's light end was unreadable.
    for (const stop of [colors.accentGradientStart, colors.accentGradientEnd]) {
      expect(contrast(colors.onAccent, stop)).toBeGreaterThanOrEqual(AA_TEXT);
    }
  });

  it('borders and dividers are distinguishable from their surface', () => {
    // Non-text content, so 3:1 rather than 4.5:1. `border` is deliberately
    // subtle and only separates two filled areas, which AA does not treat as
    // a boundary that must be perceivable on its own.
    for (const surfaceKey of ['background', 'card'] as const) {
      expect(
        contrast(colors.outline, colors[surfaceKey]),
      ).toBeGreaterThanOrEqual(AA_LARGE_OR_NON_TEXT);
    }
  });
});

describe('band scale', () => {
  it('carries a readable label on every band fill', () => {
    // BandBadge is a filled pill with the band name inside it, so the pairing
    // that matters is label-on-fill, not fill-on-card: the words do the
    // communicating and the pill is just their background.
    //
    // This is where the audit found its worst result. The label used
    // `textInverse`, which is white in the light theme, against fills that do
    // not change with the theme -- LIME at 1.98:1, AMBER at 2.15:1.
    for (const band of Object.values(BAND_SCALE)) {
      expect(contrast(ON_BRIGHT_FILL, band)).toBeGreaterThanOrEqual(AA_TEXT);
    }
  });

  it('is not confusable with the surface it sits on', () => {
    // Non-text content: 3:1 is the bar for a shape whose boundary carries
    // meaning.
    for (const band of Object.values(BAND_SCALE)) {
      expect(contrast(band, DARK_COLORS.card)).toBeGreaterThanOrEqual(
        AA_LARGE_OR_NON_TEXT,
      );
    }
  });

  it('keeps the bright semantic hues, which the deep variants replaced for text', () => {
    // Guards the split: darkening the text tokens must not quietly darken the
    // chart, and vice versa. They diverged for a reason and should stay apart.
    expect(BAND_SCALE.low).toBe(PALETTE.error);
    expect(BAND_SCALE.mid).toBe(PALETTE.warning);
    expect(BAND_SCALE.top).toBe(PALETTE.success);
    expect(LIGHT_COLORS.error).not.toBe(PALETTE.error);
  });
});

describe('readableOn', () => {
  /**
   * Every fill in the app that does not follow the theme: band pills,
   * difficulty chips, the teal accent discs, the indigo mock-test card, the
   * white splash tile. Each of these had a foreground taken from the theme,
   * which meant exactly one of the two themes was wrong.
   */
  const fixedFills = [
    ...Object.values(BAND_SCALE),
    PALETTE.teal,
    PALETTE.teal400,
    PALETTE.teal600,
    PALETTE.tealContainer,
    PALETTE.indigo,
    PALETTE.indigoTint,
    PALETTE.coral,
    PALETTE.success,
    PALETTE.warning,
    PALETTE.error,
    PALETTE.white,
  ];

  it.each(fixedFills)('picks a readable foreground for %s', fill => {
    expect(contrast(readableOn(fill), fill)).toBeGreaterThanOrEqual(AA_TEXT);
  });

  it('picks the better of the two inks, not merely an adequate one', () => {
    // Guards against the choice inverting: on a light fill the dark ink has to
    // win, and vice versa. A rule that happened to clear 4.5:1 with the worse
    // ink would still look wrong.
    expect(readableOn(PALETTE.teal400)).toBe(ON_BRIGHT_FILL);
    expect(readableOn(PALETTE.indigo)).toBe(ON_DARK_FILL);
  });

  it('serves the teal fills that use the onAccent token instead', () => {
    // Checkboxes, the coach disc and the mock-test button take `onAccent`
    // rather than calling readableOn, since it is a static style. Same
    // requirement, so it is checked here too.
    for (const fill of [PALETTE.teal, PALETTE.teal400, PALETTE.teal600]) {
      expect(contrast(LIGHT_COLORS.onAccent, fill)).toBeGreaterThanOrEqual(
        AA_TEXT,
      );
      expect(contrast(DARK_COLORS.onAccent, fill)).toBeGreaterThanOrEqual(
        AA_TEXT,
      );
    }
  });
});

describe('theme parity', () => {
  it('defines the same keys in both themes', () => {
    // A key present in one theme and missing from the other is `undefined` at
    // render time: invisible text, or a crash in a style array. TypeScript
    // does not catch it, because each object is inferred independently.
    expect(Object.keys(LIGHT_COLORS).sort()).toEqual(
      Object.keys(DARK_COLORS).sort(),
    );
  });

  it('gives every key a usable value in both themes', () => {
    for (const [name, theme] of themes) {
      for (const [key, value] of Object.entries(theme)) {
        expect({ key: `${name}.${key}`, value }).toMatchObject({
          value: expect.stringMatching(/^(#[0-9A-Fa-f]{6}|rgba?\(.+\))$/),
        });
      }
    }
  });

  it('does not reuse a light surface as a dark one', () => {
    // The cheapest possible check that dark mode is a real theme rather than
    // the light one with a few keys renamed.
    for (const key of surfaceKeys) {
      expect(luminance(DARK_COLORS[key])).toBeLessThan(
        luminance(LIGHT_COLORS[key]),
      );
    }
  });
});
