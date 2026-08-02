/** Onboarding: welcome carousel and the exam-setup step. */

import React from 'react';
import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import { Welcome } from '../Onboarding/Welcome/Welcome';
import { SLIDES } from '../Onboarding/Welcome/useWelcome';
import { ExamSetup } from '../Onboarding/ExamSetup/ExamSetup';
import { Diagnostic } from '../Onboarding/Diagnostic/Diagnostic';
import { renderWithProviders } from '../../testUtils/renderWithProviders';

describe('Welcome carousel', () => {
  it('opens on the first slide with a skip route out', () => {
    renderWithProviders(<Welcome />);
    expect(screen.getByTestId('welcome-pager')).toBeTruthy();
    expect(screen.getByText(SLIDES[0].title)).toBeTruthy();
    // Nobody should be trapped in an intro.
    expect(screen.getByTestId('welcome-skip')).toBeTruthy();
  });

  it('renders every slide and a dot for each', () => {
    renderWithProviders(<Welcome />);
    SLIDES.forEach((slide) => {
      expect(screen.getByText(slide.title)).toBeTruthy();
      expect(screen.getByTestId(`welcome-slide-${slide.icon}`)).toBeTruthy();
    });
    expect(screen.getByTestId('welcome-dots')).toBeTruthy();
  });

  it('advances through the slides before offering to start', () => {
    renderWithProviders(<Welcome />);
    const button = screen.getByTestId('welcome-next');
    expect(button).toHaveTextContent('Next');

    fireEvent.press(button);
    fireEvent.press(screen.getByTestId('welcome-next'));

    // Last slide swaps the label rather than silently doing something else.
    expect(screen.getByTestId('welcome-next')).toHaveTextContent('Get started');
  });

  it('promises only what the app actually does', () => {
    // Guards against marketing copy drifting ahead of the product.
    const copy = SLIDES.map((s) => `${s.title} ${s.body}`).join(' ').toLowerCase();
    expect(copy).not.toMatch(/guarantee|guaranteed|band 9 in|certified/);
  });
});

describe('Exam setup step', () => {
  it('offers an optional exam date', async () => {
    renderWithProviders(<ExamSetup />);
    await waitFor(() => {
      expect(screen.getByText('Exam date')).toBeTruthy();
    });
    // Optional on purpose: many learners have not booked yet.
    expect(screen.getByText('Not decided yet')).toBeTruthy();
    expect(screen.getByTestId('onboarding-set-date')).toBeTruthy();
  });

  it('opens the date picker on request', async () => {
    renderWithProviders(<ExamSetup />);
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-set-date')).toBeTruthy();
    });
    fireEvent.press(screen.getByTestId('onboarding-set-date'));
    await waitFor(() => {
      expect(screen.getByText('When is your exam?')).toBeTruthy();
    });
  });
});

describe('Placement diagnostic', () => {
  it('opens on the reading step with progress shown', async () => {
    renderWithProviders(<Diagnostic />);
    await waitFor(() => {
      expect(screen.getByText(/Step 1 of 4 · Reading/)).toBeTruthy();
    });
    // Skippable from the very first screen: a placement test nobody can
    // escape is a wall, not an on-ramp.
    expect(screen.getByTestId('diagnostic-skip')).toBeTruthy();
  });

  it('steps forward through all four sections', async () => {
    renderWithProviders(<Diagnostic />);
    await waitFor(() => {
      expect(screen.getByTestId('diagnostic-next')).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId('diagnostic-next'));
    await waitFor(() => {
      expect(screen.getByText(/Step 2 of 4/)).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId('diagnostic-next'));
    await waitFor(() => {
      expect(screen.getByTestId('diagnostic-writing')).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId('diagnostic-next'));
    await waitFor(() => {
      expect(screen.getByTestId('diagnostic-speaking')).toBeTruthy();
    });
    // Last step scores rather than advancing.
    expect(screen.getByTestId('diagnostic-next')).toHaveTextContent('See my level');
  });

  it('says plainly that listening audio is not playable yet', async () => {
    renderWithProviders(<Diagnostic />);
    await waitFor(() => {
      expect(screen.getByTestId('diagnostic-next')).toBeTruthy();
    });
    fireEvent.press(screen.getByTestId('diagnostic-next'));
    await waitFor(() => {
      expect(
        screen.getByText(/Audio playback is not available yet/),
      ).toBeTruthy();
    });
  });

  it('shows the word minimum on free-text steps', async () => {
    renderWithProviders(<Diagnostic />);
    await waitFor(() => {
      expect(screen.getByTestId('diagnostic-next')).toBeTruthy();
    });
    fireEvent.press(screen.getByTestId('diagnostic-next'));
    fireEvent.press(screen.getByTestId('diagnostic-next'));
    await waitFor(() => {
      // Below the minimum nothing is scored, so the threshold is stated.
      expect(screen.getByText('0 / 40 words minimum')).toBeTruthy();
    });
  });

  it('reports unmeasured modules without inventing a band', async () => {
    renderWithProviders(<Diagnostic />);
    await waitFor(() => {
      expect(screen.getByTestId('diagnostic-next')).toBeTruthy();
    });
    for (let i = 0; i < 3; i += 1) {
      fireEvent.press(screen.getByTestId('diagnostic-next'));
    }
    fireEvent.press(screen.getByTestId('diagnostic-next'));

    await waitFor(() => {
      expect(screen.getByTestId('diagnostic-result')).toBeTruthy();
    });
    expect(screen.getByText('CEFR B2')).toBeTruthy();
    // A skipped module reads "Not measured", never 0.0.
    expect(screen.getByText('Not measured')).toBeTruthy();
    expect(screen.getByText(/excluded rather than guessed/)).toBeTruthy();
  });
});
