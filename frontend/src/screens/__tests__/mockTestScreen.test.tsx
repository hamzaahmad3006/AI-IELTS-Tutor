/** Full mock test: sitting flow and the readiness report. */

import React from 'react';
import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import { MockTest } from '../MockTest/MockTest';
import { renderWithProviders } from '../../testUtils/renderWithProviders';

const startSitting = async (): Promise<void> => {
  fireEvent.press(screen.getByTestId('mock-start'));
  await waitFor(() => {
    expect(screen.getByTestId('mock-timer')).toBeTruthy();
  });
};

describe('Full mock test', () => {
  it('explains the sitting before it begins', () => {
    renderWithProviders(<MockTest />);
    expect(screen.getByTestId('mock-intro')).toBeTruthy();
    // Skipping is stated up front, not discovered in the report.
    expect(screen.getByText(/the report will say so rather/)).toBeTruthy();
  });

  it('starts on Listening with its real 30-minute allowance', async () => {
    renderWithProviders(<MockTest />);
    await startSitting();
    expect(screen.getByTestId('mock-section-listening')).toBeTruthy();
    expect(screen.getByTestId('timer-clock')).toHaveTextContent('30:00');
  });

  it('re-arms the clock for each section', async () => {
    renderWithProviders(<MockTest />);
    await startSitting();

    fireEvent.press(screen.getByTestId('mock-next'));
    await waitFor(() => {
      expect(screen.getByTestId('mock-section-reading')).toBeTruthy();
    });
    // Reading gets 60 minutes, not the remainder of Listening's budget.
    expect(screen.getByTestId('timer-clock')).toHaveTextContent('60:00');
  });

  it('offers writing and speaking as free text', async () => {
    renderWithProviders(<MockTest />);
    await startSitting();
    fireEvent.press(screen.getByTestId('mock-next'));
    fireEvent.press(screen.getByTestId('mock-next'));
    await waitFor(() => {
      expect(screen.getByTestId('mock-writing')).toBeTruthy();
    });
    fireEvent.press(screen.getByTestId('mock-next'));
    await waitFor(() => {
      expect(screen.getByTestId('mock-speaking')).toBeTruthy();
    });
    // Last section scores rather than advancing.
    expect(screen.getByTestId('mock-next')).toHaveTextContent(
      'Finish and see report',
    );
  });

  it('reports the verdict, each section and what to do next', async () => {
    renderWithProviders(<MockTest />);
    await startSitting();
    for (let i = 0; i < 4; i += 1) {
      fireEvent.press(screen.getByTestId('mock-next'));
    }
    await waitFor(() => {
      expect(screen.getByTestId('mock-report')).toBeTruthy();
    });
    expect(screen.getByText('NEARLY READY')).toBeTruthy();
    expect(screen.getByText('BY SECTION')).toBeTruthy();
    // The report says what to do, not just what happened.
    expect(screen.getByText('WHAT TO DO NEXT')).toBeTruthy();
    expect(screen.getByText(/weakest section is writing/)).toBeTruthy();
  });
});
