/**
 * The arithmetic behind the progress ring and streak flame.
 *
 * Extracted from the components because SVG attributes are not queryable in
 * React Native's test renderer — you cannot assert that an arc is the right
 * length by looking at rendered output. Pure functions can be tested exactly,
 * and the drawing that consumes them is then trivial enough to read.
 */

/** Circumference of the stroked path, for dash-offset arithmetic. */
export const circumference = (radius: number): number => 2 * Math.PI * radius;

/**
 * Fraction of the ring to fill, from a value and its goal.
 *
 * Clamped to [0, 1]. A learner who doubles their goal gets a full ring, not a
 * second lap: an over-full ring reads as a rendering bug, and "247%" reads as
 * a warning rather than as praise.
 */
export const fractionOf = (value: number, goal: number): number => {
  if (!Number.isFinite(value) || !Number.isFinite(goal) || goal <= 0) {
    return 0;
  }
  return Math.min(1, Math.max(0, value / goal));
};

/**
 * Dash offset that draws `fraction` of the ring.
 *
 * Offset counts backwards from a full circle, so fraction 0 must offset by the
 * whole circumference and fraction 1 by none. Getting this inverted draws a
 * ring that empties as the learner progresses, which looks deliberate and is
 * therefore easy to miss.
 */
export const dashOffset = (radius: number, fraction: number): number =>
  circumference(radius) * (1 - fractionOf(fraction, 1));

/**
 * How intense the streak flame should look, 0 to 1.
 *
 * Logarithmic, not linear. A linear scale against some arbitrary maximum makes
 * day 3 look like nothing, and the early days are exactly when a learner needs
 * the encouragement — by day 60 they are not checking the flame. Growth is fast
 * at first and flattens, which is also how the achievement actually feels.
 */
export const flameIntensity = (streakDays: number): number => {
  if (streakDays <= 0) {
    return 0;
  }
  // log2(1 + days) / log2(1 + 30): a 30-day streak reaches full intensity,
  // day 1 is already visible, and beyond 30 it simply stays lit.
  return Math.min(1, Math.log2(1 + streakDays) / Math.log2(31));
};

/** Whether the flame is lit at all. A zero-day streak must not glow faintly. */
export const isStreakAlive = (streakDays: number): boolean => streakDays > 0;

/**
 * Label for the streak.
 *
 * "1 day", not "1 days". Plural bugs are small and make an app feel unfinished
 * in a way people notice without being able to say why.
 */
export const streakLabel = (streakDays: number): string => {
  if (streakDays <= 0) {
    return 'No streak yet';
  }
  return streakDays === 1 ? '1 day streak' : `${streakDays} day streak`;
};
