/** Study plan screen: weeks, task completion and rebuild. */

import React from 'react';
import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import { Plan } from '../Plan/Plan';
import { renderWithProviders } from '../../testUtils/renderWithProviders';

describe('Study plan screen', () => {
  it('shows progress and the rationale behind the plan', async () => {
    renderWithProviders(<Plan />);
    await waitFor(() => {
      expect(screen.getByTestId('plan-summary')).toBeTruthy();
    });
    expect(screen.getByText('1 of 6 sessions done')).toBeTruthy();
    // A plan the learner cannot interrogate is just a list of chores.
    expect(screen.getByText(/weighted towards the modules furthest/)).toBeTruthy();
  });

  it('lists one chip per week and shows only that week', async () => {
    renderWithProviders(<Plan />);
    await waitFor(() => {
      expect(screen.getByTestId('plan-week-1')).toBeTruthy();
    });
    expect(screen.getByTestId('plan-week-2')).toBeTruthy();

    // Week 1 has five sessions in the fixture, week 2 has one.
    expect(screen.getByTestId('plan-task-pt1')).toBeTruthy();
    expect(screen.queryByTestId('plan-task-pt6')).toBeNull();

    fireEvent.press(screen.getByTestId('plan-week-2'));
    await waitFor(() => {
      expect(screen.getByTestId('plan-task-pt6')).toBeTruthy();
    });
    expect(screen.queryByTestId('plan-task-pt1')).toBeNull();
  });

  it('ticks a task off immediately', async () => {
    renderWithProviders(<Plan />);
    await waitFor(() => {
      expect(screen.getByTestId('plan-task-pt2')).toBeTruthy();
    });
    expect(
      screen.getByTestId('plan-task-pt2').props.accessibilityState,
    ).toEqual(expect.objectContaining({ checked: false }));

    fireEvent.press(screen.getByTestId('plan-task-pt2'));

    // Optimistic: the tick lands before the request resolves.
    await waitFor(() => {
      expect(
        screen.getByTestId('plan-task-pt2').props.accessibilityState,
      ).toEqual(expect.objectContaining({ checked: true }));
    });
    expect(screen.getByText('2 of 6 sessions done')).toBeTruthy();
  });

  it('offers a rebuild', async () => {
    renderWithProviders(<Plan />);
    await waitFor(() => {
      expect(screen.getByTestId('plan-rebuild')).toBeTruthy();
    });
    fireEvent.press(screen.getByTestId('plan-rebuild'));
    await waitFor(() => {
      expect(screen.getByTestId('plan-summary')).toBeTruthy();
    });
  });
});
