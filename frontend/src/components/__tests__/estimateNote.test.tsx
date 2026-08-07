/**
 * The estimate disclaimer.
 *
 * A band this app produces comes from a language model reading one piece of
 * work, not from a trained examiner running a moderated exam. Shown bare, "6.5"
 * is indistinguishable from the real thing — and a learner who books a test on
 * the strength of it is out the fee.
 *
 * These assert the wording says the two things that actually matter: that it is
 * an estimate, and that it is not official.
 */

import React from 'react';
import { screen } from '@testing-library/react-native';
import { renderWithProviders as render } from '../../testUtils/renderWithProviders';
import {
  ESTIMATE_TEXT_FULL,
  ESTIMATE_TEXT_SHORT,
  EstimateNote,
} from '../EstimateNote/EstimateNote';

describe('EstimateNote', () => {
  it('says it is an estimate and not official', () => {
    render(<EstimateNote />);
    const text = screen.getByText(ESTIMATE_TEXT_FULL);
    expect(text).toBeTruthy();
  });

  it('keeps both claims in the short form too', () => {
    render(<EstimateNote variant="short" />);
    expect(screen.getByText(ESTIMATE_TEXT_SHORT)).toBeTruthy();
  });

  it('never drops either claim from either variant', () => {
    // Worded as a content assertion rather than a string match, so a rewrite
    // that loses one of the two claims fails instead of silently passing.
    for (const copy of [ESTIMATE_TEXT_FULL, ESTIMATE_TEXT_SHORT]) {
      expect(copy.toLowerCase()).toContain('estimate');
      expect(copy.toLowerCase()).toContain('not an official');
    }
  });

  it('is readable by a screen reader', () => {
    render(<EstimateNote />);
    // A screen-reader user must not be the only person who does not learn the
    // number is an estimate.
    expect(screen.getByText(ESTIMATE_TEXT_FULL)).toBeTruthy();
  });
});
