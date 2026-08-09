/**
 * Turning microphone metering into bar heights.
 *
 * Android reports input level in decibels full scale: 0 dB is the loudest the
 * hardware can encode and everything quieter is negative, typically down to
 * about -60 dB for a silent room. Plotting that directly produces a waveform
 * that sits pinned at the bottom, because ordinary speech lives around -20 dB
 * and the visual range between "silent" and "talking" is a tenth of the axis.
 *
 * So the scale is normalised over the range that actually matters — a quiet
 * room to a raised voice — and everything outside it clamps. The point of the
 * bars is to answer "can you hear me?", which needs obvious movement at
 * conversational volume, not an accurate meter.
 *
 * Pure functions, because SVG and animated bar heights are not assertable in
 * React Native's test renderer.
 */

/** Quieter than this is silence as far as the display is concerned. */
export const FLOOR_DB = -50;

/** Louder than this is already a full bar; shouting should not add headroom. */
export const CEILING_DB = -10;

/** Bars kept on screen. Enough to read as a waveform, few enough to stay cheap. */
export const BAR_COUNT = 24;

/** Never zero: a flat line reads as a dead microphone rather than a quiet one. */
export const MIN_BAR = 0.08;

/**
 * Map a decibel reading to 0..1.
 *
 * A missing or non-finite reading is silence rather than an error. Metering
 * drops out briefly on some devices, and a NaN propagated into a bar height
 * collapses the whole waveform.
 */
export const normalise = (db: number | null | undefined): number => {
  if (db === null || db === undefined || !Number.isFinite(db)) {
    return 0;
  }
  if (db <= FLOOR_DB) {
    return 0;
  }
  if (db >= CEILING_DB) {
    return 1;
  }
  return (db - FLOOR_DB) / (CEILING_DB - FLOOR_DB);
};

/**
 * Bar height for a reading, as a fraction of the track.
 *
 * Square-rooted. Loudness is perceived roughly logarithmically, so a linear
 * mapping makes normal speech look timid and only shouting look active — the
 * opposite of a reassuring indicator.
 */
export const barHeight = (db: number | null | undefined): number => {
  const level = normalise(db);
  return MIN_BAR + (1 - MIN_BAR) * Math.sqrt(level);
};

/**
 * Append a reading to the rolling window.
 *
 * Returns a new array rather than mutating, so React sees a changed reference.
 * Mutating in place is the version of this that renders once and then appears
 * frozen.
 */
export const pushLevel = (
  history: readonly number[],
  db: number | null | undefined,
  size: number = BAR_COUNT,
): number[] => {
  const next = [...history, barHeight(db)];
  return next.length > size ? next.slice(next.length - size) : next;
};

/** A full window of silence, so the bar count is stable from the first frame. */
export const idleLevels = (size: number = BAR_COUNT): number[] =>
  new Array(size).fill(MIN_BAR);
