/**
 * Ring geometry and streak intensity.
 *
 * Tested as functions rather than through the rendered SVG, because SVG
 * attributes are not queryable in React Native's test renderer — you cannot
 * assert an arc is the right length by looking at output. These are the numbers
 * the drawing consumes, and a wrong one produces a ring that looks deliberate.
 */

import {
  circumference,
  dashOffset,
  flameIntensity,
  fractionOf,
  isStreakAlive,
  streakLabel,
} from '../ProgressRing/geometry';

describe('fractionOf', () => {
  it('is the plain ratio in the ordinary case', () => {
    expect(fractionOf(15, 30)).toBe(0.5);
    expect(fractionOf(30, 30)).toBe(1);
    expect(fractionOf(0, 30)).toBe(0);
  });

  it('caps at a full ring', () => {
    // A learner who doubles their goal gets a full ring, not a second lap:
    // an over-full ring reads as a rendering bug.
    expect(fractionOf(90, 30)).toBe(1);
  });

  it('never goes negative', () => {
    expect(fractionOf(-10, 30)).toBe(0);
  });

  it('survives a nonsense goal instead of rendering NaN', () => {
    // A NaN dash offset makes the whole ring disappear, which looks like a
    // broken component rather than like missing data.
    for (const goal of [0, -1, NaN, Infinity]) {
      expect(fractionOf(10, goal)).toBe(0);
    }
    expect(fractionOf(NaN, 30)).toBe(0);
  });
});

describe('dashOffset', () => {
  const r = 60;

  it('offsets by the whole circumference when empty', () => {
    expect(dashOffset(r, 0)).toBeCloseTo(circumference(r));
  });

  it('offsets by nothing when full', () => {
    expect(dashOffset(r, 1)).toBeCloseTo(0);
  });

  it('decreases as progress increases', () => {
    // Inverted, this draws a ring that empties as the learner progresses —
    // which looks deliberate and is therefore easy to miss.
    expect(dashOffset(r, 0.25)).toBeGreaterThan(dashOffset(r, 0.75));
  });
});

describe('flameIntensity', () => {
  it('is dark with no streak', () => {
    expect(flameIntensity(0)).toBe(0);
    expect(flameIntensity(-3)).toBe(0);
  });

  it('is already visible on day one', () => {
    // The early days are exactly when a learner needs the encouragement; by
    // day 60 they are not checking the flame.
    expect(flameIntensity(1)).toBeGreaterThan(0.15);
  });

  it('grows fast then flattens', () => {
    const early = flameIntensity(3) - flameIntensity(1);
    const late = flameIntensity(30) - flameIntensity(28);
    expect(early).toBeGreaterThan(late);
  });

  it('reaches full and stays there', () => {
    expect(flameIntensity(30)).toBeCloseTo(1, 5);
    expect(flameIntensity(365)).toBe(1);
  });
});

describe('streakLabel', () => {
  it('says nothing encouraging when there is no streak', () => {
    expect(streakLabel(0)).toBe('No streak yet');
    expect(isStreakAlive(0)).toBe(false);
  });

  it('gets the singular right', () => {
    // "1 days" is small and makes an app feel unfinished in a way people
    // notice without being able to say why.
    expect(streakLabel(1)).toBe('1 day streak');
    expect(streakLabel(2)).toBe('2 day streak');
  });
});
