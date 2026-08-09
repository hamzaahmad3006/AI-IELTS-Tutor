/**
 * Microphone level to bar height.
 *
 * Tested as functions: animated bar heights are not assertable in React
 * Native's test renderer, and these are the numbers the drawing consumes.
 *
 * The recurring failure they guard is a waveform that sits flat while someone
 * is talking — which tells a candidate the app cannot hear them when it can.
 */

import {
  BAR_COUNT,
  CEILING_DB,
  FLOOR_DB,
  MIN_BAR,
  barHeight,
  idleLevels,
  normalise,
  pushLevel,
} from '../Waveform/levels';

describe('normalise', () => {
  it('treats a quiet room as silence', () => {
    expect(normalise(FLOOR_DB)).toBe(0);
    expect(normalise(-80)).toBe(0);
  });

  it('saturates at a raised voice', () => {
    // Shouting must not add headroom: the bar is already full at conversational
    // volume, which is where the reassurance is needed.
    expect(normalise(CEILING_DB)).toBe(1);
    expect(normalise(0)).toBe(1);
  });

  it('puts ordinary speech in the middle of the range', () => {
    // Around -20 dBFS is normal talking. Plotting raw dB would leave this
    // pinned near the bottom, because the useful range is a tenth of the axis.
    const speech = normalise(-20);
    expect(speech).toBeGreaterThan(0.5);
    expect(speech).toBeLessThan(1);
  });

  it('treats a dropped reading as silence rather than breaking', () => {
    // Metering drops out briefly on some devices; a NaN propagated into a bar
    // height collapses the entire waveform.
    for (const reading of [null, undefined, NaN, Infinity, -Infinity]) {
      expect(normalise(reading as number)).toBe(0);
    }
  });
});

describe('barHeight', () => {
  it('never reaches zero', () => {
    // A flat line reads as a dead microphone rather than a quiet one.
    expect(barHeight(-100)).toBe(MIN_BAR);
    expect(barHeight(null)).toBe(MIN_BAR);
  });

  it('fills at the ceiling', () => {
    expect(barHeight(CEILING_DB)).toBeCloseTo(1);
  });

  it('rises faster than linearly at speaking volume', () => {
    // Loudness is perceived roughly logarithmically. A linear mapping makes
    // normal speech look timid and only shouting look active, which is the
    // opposite of a reassuring indicator.
    const midDb = (FLOOR_DB + CEILING_DB) / 2;
    const linear = MIN_BAR + (1 - MIN_BAR) * 0.5;
    expect(barHeight(midDb)).toBeGreaterThan(linear);
  });

  it('is monotonic', () => {
    let last = -1;
    for (let db = -60; db <= 0; db += 2) {
      const height = barHeight(db);
      expect(height).toBeGreaterThanOrEqual(last);
      last = height;
    }
  });
});

describe('pushLevel', () => {
  it('appends and keeps the window bounded', () => {
    let history = idleLevels(4);
    for (let i = 0; i < 20; i += 1) {
      history = pushLevel(history, -20, 4);
    }
    expect(history).toHaveLength(4);
  });

  it('drops the oldest reading first', () => {
    const history = pushLevel([0.1, 0.2, 0.3], -10, 3);
    expect(history).toHaveLength(3);
    expect(history[0]).toBe(0.2);
    expect(history[2]).toBeCloseTo(1);
  });

  it('returns a new array', () => {
    // Mutating in place is the version that renders once and then looks frozen,
    // because React never sees a changed reference.
    const original = idleLevels(3);
    const next = pushLevel(original, -20, 3);
    expect(next).not.toBe(original);
    expect(original).toEqual(idleLevels(3));
  });
});

describe('idleLevels', () => {
  it('is a full window of minimum bars', () => {
    const idle = idleLevels();
    expect(idle).toHaveLength(BAR_COUNT);
    // Stable bar count from the first frame, so the waveform does not grow
    // sideways as readings arrive.
    expect(new Set(idle)).toEqual(new Set([MIN_BAR]));
  });
});
