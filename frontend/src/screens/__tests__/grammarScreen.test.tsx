/** Render + interaction tests for the grammar lessons screen. */

import React from 'react';
import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import { Lessons } from '../Grammar/Lessons/Lessons';
import { renderWithProviders } from '../../testUtils/renderWithProviders';

describe('Grammar lessons screen', () => {
  it('lists lessons and highlights ones targeting the learner', async () => {
    renderWithProviders(<Lessons />);

    await waitFor(() => {
      expect(screen.getByText('Subject-verb agreement')).toBeTruthy();
    });
    expect(screen.getByText('Articles: a, an and the')).toBeTruthy();
    // Recommended lessons are badged and announced in the banner.
    expect(screen.getByText('FOR YOU')).toBeTruthy();
    expect(
      screen.getByText(/target\s+mistakes the AI examiner found/),
    ).toBeTruthy();
  });

  it('opens a lesson and shows the explanation and examples', async () => {
    renderWithProviders(<Lessons />);
    await waitFor(() => {
      expect(screen.getByText('Subject-verb agreement')).toBeTruthy();
    });

    fireEvent.press(screen.getByText('Subject-verb agreement'));

    await waitFor(() => {
      expect(screen.getByText('Examples')).toBeTruthy();
    });
    // The corrected example is shown alongside the incorrect one.
    expect(
      screen.getByText('The number of students is increasing.'),
    ).toBeTruthy();
    expect(screen.getByText('Back to lessons')).toBeTruthy();
  });

  it('returns to the library from a lesson', async () => {
    renderWithProviders(<Lessons />);
    await waitFor(() =>
      expect(screen.getByText('Subject-verb agreement')).toBeTruthy(),
    );

    fireEvent.press(screen.getByText('Subject-verb agreement'));
    await waitFor(() =>
      expect(screen.getByText('Back to lessons')).toBeTruthy(),
    );

    fireEvent.press(screen.getByText('Back to lessons'));

    await waitFor(() => {
      expect(screen.getByText('Articles: a, an and the')).toBeTruthy();
    });
  });
});
