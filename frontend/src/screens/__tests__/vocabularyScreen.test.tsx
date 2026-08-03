/** Render + interaction tests for the vocabulary review flashcards. */

import React from 'react';
import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import { Review } from '../Vocabulary/Review/Review';
import { renderWithProviders } from '../../testUtils/renderWithProviders';

describe('Vocabulary review screen', () => {
  it('shows a card with the answer hidden until revealed', async () => {
    renderWithProviders(<Review />);

    await waitFor(() => {
      expect(screen.getByText('detrimental')).toBeTruthy();
    });
    // The definition stays hidden until the learner commits to an answer.
    expect(screen.queryByText('Tending to cause harm or damage.')).toBeNull();
    expect(screen.getByText('Show definition')).toBeTruthy();
  });

  it('reveals the definition and offers recall grades', async () => {
    renderWithProviders(<Review />);
    await waitFor(() => {
      expect(screen.getByText('Show definition')).toBeTruthy();
    });

    fireEvent.press(screen.getByText('Show definition'));

    await waitFor(() => {
      expect(screen.getByText('Tending to cause harm or damage.')).toBeTruthy();
    });
    ['Forgot', 'Hard', 'Good', 'Easy'].forEach(label => {
      expect(screen.getByText(label)).toBeTruthy();
    });
  });

  it('advances to the next card after grading', async () => {
    renderWithProviders(<Review />);
    await waitFor(() => {
      expect(screen.getByText('detrimental')).toBeTruthy();
    });

    fireEvent.press(screen.getByText('Show definition'));
    await waitFor(() => expect(screen.getByText('Good')).toBeTruthy());
    fireEvent.press(screen.getByText('Good'));

    // Second card is shown, with its answer hidden again.
    await waitFor(() => {
      expect(screen.getByText('mitigate')).toBeTruthy();
    });
    expect(screen.getByText('Show definition')).toBeTruthy();
  });
});
