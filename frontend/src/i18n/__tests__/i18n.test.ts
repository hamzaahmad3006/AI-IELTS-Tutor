/**
 * Localisation.
 *
 * The assertions are about the failure modes that reach a user: a placeholder
 * rendered as "undefined", a missing key rendered as nothing at all, and IELTS
 * terminology being translated into words the examiner will not use.
 */

import { en } from '../en';
import {
  DEFAULT_LOCALE,
  deviceLocale,
  getLocale,
  setLocale,
  t,
  type TranslationKey,
} from '../index';

describe('t', () => {
  beforeEach(() => setLocale(DEFAULT_LOCALE));

  it('returns the string for a key', () => {
    expect(t('interview.ready')).toBe("I'm ready");
  });

  it('substitutes placeholders', () => {
    expect(t('a11y.band', { band: 6.5 })).toBe('Estimated band 6.5 out of 9');
    expect(t('a11y.progress', { done: 3, total: 9 })).toBe('3 of 9 complete');
  });

  it('leaves an unsupplied placeholder visible', () => {
    // A visible {band} is obviously a bug to whoever sees it. "Estimated band
    // undefined out of 9" reads like a broken app to the user and like working
    // software to everyone else.
    expect(t('a11y.band')).toContain('{band}');
    expect(t('a11y.band', { wrong: 1 })).not.toContain('undefined');
  });

  it('returns the key itself when it is missing', () => {
    // Ugly and unmistakable beats an empty string, which produces a blank
    // space nobody ever reports.
    expect(t('does.not.exist' as TranslationKey)).toBe('does.not.exist');
  });

  it('has no empty strings', () => {
    const empty = Object.entries(en).filter(([, value]) => !value.trim());
    expect(empty).toEqual([]);
  });

  it('keeps IELTS terminology in English', () => {
    // "Band", "Task 1" and "cue card" are printed on the real exam paper
    // wherever it is sat. Translating them teaches vocabulary the examiner
    // will not use.
    expect(t('score.estimateShort')).toContain('IELTS');
    expect(t('interview.phase.part1')).toContain('Part 1');
  });

  it('says both things in the estimate disclaimer', () => {
    for (const key of [
      'score.estimateFull',
      'score.estimateShort',
    ] as TranslationKey[]) {
      expect(t(key).toLowerCase()).toContain('estimate');
      expect(t(key).toLowerCase()).toContain('not an official');
    }
  });

  it('writes accessibility labels as spoken sentences', () => {
    // Read aloud, not shown. "Record" tells a screen-reader user nothing about
    // what will happen.
    expect(t('a11y.record.start')).toBe('Start recording your answer');
    expect(t('a11y.record.start').split(' ').length).toBeGreaterThan(2);
  });
});

describe('locale', () => {
  it('defaults to English', () => {
    setLocale(DEFAULT_LOCALE);
    expect(getLocale()).toBe('en');
  });

  it('falls back to English for an unsupported device locale', () => {
    // The native modules that expose this differ by platform and have moved
    // between React Native versions; a missing locale must mean English, not
    // a crash on the first render.
    expect(deviceLocale()).toBe('en');
  });
});
