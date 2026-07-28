/**
 * Render tests for the data-driven practice screens.
 *
 * These mount each screen with its real hook against the mock API layer, which
 * exercises the loading -> loaded transition and catches render-time crashes
 * that a typecheck cannot.
 */

import React from 'react';
import { screen, waitFor } from '@testing-library/react-native';
import { Practice as ReadingPractice } from '../Reading/Practice/Practice';
import { Practice as ListeningPractice } from '../Listening/Practice/Practice';
import { Practice as WritingPractice } from '../Writing/Practice/Practice';
import { Practice as SpeakingPractice } from '../Speaking/Practice/Practice';
import { renderWithProviders } from '../../testUtils/renderWithProviders';

describe('Reading practice screen', () => {
  it('loads a passage and renders its questions', async () => {
    renderWithProviders(<ReadingPractice />);
    await waitFor(() => {
      expect(screen.getByText('The History of Tea')).toBeTruthy();
    });
    // Submit button shows answered/total progress.
    expect(screen.getByText('Submit (0/3)')).toBeTruthy();
    // First question prompt is rendered with its index.
    expect(screen.getByText(/Where did tea originate/)).toBeTruthy();
  });
});

describe('Listening practice screen', () => {
  it('loads a clip and renders the player and questions', async () => {
    renderWithProviders(<ListeningPractice />);
    await waitFor(() => {
      expect(screen.getByText('University Orientation')).toBeTruthy();
    });
    expect(screen.getByText('Tap play to listen')).toBeTruthy();
    expect(screen.getByText('Submit answers')).toBeTruthy();
  });
});

describe('Writing practice screen', () => {
  it('renders the prompt and editor', async () => {
    renderWithProviders(<WritingPractice />);
    await waitFor(() => {
      expect(screen.getByText('PROMPT')).toBeTruthy();
    });
    expect(screen.getByPlaceholderText('Write your essay here…')).toBeTruthy();
    expect(screen.getByText('Submit for AI scoring')).toBeTruthy();
    // Word count starts at zero.
    expect(screen.getByText('0 words')).toBeTruthy();
  });
});

describe('Speaking practice screen', () => {
  it('renders the cue card and prep phase', async () => {
    renderWithProviders(<SpeakingPractice />);
    await waitFor(() => {
      expect(screen.getByText(/CUE CARD/)).toBeTruthy();
    });
    expect(screen.getByText('Preparation time')).toBeTruthy();
    expect(screen.getByText('Start speaking')).toBeTruthy();
  });
});
