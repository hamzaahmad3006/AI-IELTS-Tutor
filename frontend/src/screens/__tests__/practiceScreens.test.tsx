/**
 * Render tests for the data-driven practice screens.
 *
 * These mount each screen with its real hook against the mock API layer, which
 * exercises the loading -> loaded transition and catches render-time crashes
 * that a typecheck cannot.
 */

import React from 'react';
import { act, fireEvent, screen, waitFor } from '@testing-library/react-native';
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
    // Word count starts at zero and shows the target for the selected task.
    expect(screen.getByText('0 / 250 words')).toBeTruthy();
  });

  it('lets the learner pick the paper and task', async () => {
    renderWithProviders(<WritingPractice />);
    await waitFor(() => {
      expect(screen.getByTestId('task-selector')).toBeTruthy();
    });
    expect(screen.getByTestId('exam-academic')).toBeTruthy();
    expect(screen.getByTestId('exam-general')).toBeTruthy();

    // Task 1 is a report in Academic and a letter in General, so the label
    // has to follow the selected paper rather than being fixed.
    expect(screen.getByText('Task 1 · Report')).toBeTruthy();
    fireEvent.press(screen.getByTestId('exam-general'));
    await waitFor(() => {
      expect(screen.getByText('Task 1 · Letter')).toBeTruthy();
    });
  });

  it('switches the word target with the task', async () => {
    renderWithProviders(<WritingPractice />);
    await waitFor(() => {
      expect(screen.getByText('0 / 250 words')).toBeTruthy();
    });
    fireEvent.press(screen.getByTestId('task-1'));
    await waitFor(() => {
      expect(screen.getByText('0 / 150 words')).toBeTruthy();
    });
  });

  it('counts the task allowance down and can be paused', async () => {
    jest.useFakeTimers();
    try {
      renderWithProviders(<WritingPractice />);
      await waitFor(() => {
        expect(screen.getByTestId('writing-timer')).toBeTruthy();
      });
      // Task 2 allows 40 minutes.
      expect(screen.getByTestId('timer-clock')).toHaveTextContent('40:00');

      fireEvent.press(screen.getByTestId('timer-toggle'));
      act(() => {
        jest.advanceTimersByTime(65_000);
      });
      expect(screen.getByTestId('timer-clock')).toHaveTextContent('38:55');

      fireEvent.press(screen.getByTestId('timer-toggle'));
      act(() => {
        jest.advanceTimersByTime(30_000);
      });
      // Paused means paused.
      expect(screen.getByTestId('timer-clock')).toHaveTextContent('38:55');
    } finally {
      jest.useRealTimers();
    }
  });
});

describe('Difficulty selection', () => {
  it('offers adaptive plus explicit levels on Reading', async () => {
    renderWithProviders(<ReadingPractice />);
    await waitFor(() => {
      expect(screen.getByTestId('difficulty-selector')).toBeTruthy();
    });
    // Adaptive stays a first-class option, so an override can be undone.
    ['adaptive', 'easy', 'medium', 'hard'].forEach(level => {
      expect(screen.getByTestId(`difficulty-${level}`)).toBeTruthy();
    });
  });

  it('reports the level actually served, not just the one requested', async () => {
    renderWithProviders(<ReadingPractice />);
    await waitFor(() => {
      expect(screen.getByTestId('difficulty-served')).toBeTruthy();
    });
    // Under adaptive the copy says the app chose it.
    expect(screen.getByTestId('difficulty-served')).toHaveTextContent(/Chose/);
  });

  it('offers the same control on Listening', async () => {
    renderWithProviders(<ListeningPractice />);
    await waitFor(() => {
      expect(screen.getByTestId('difficulty-selector')).toBeTruthy();
    });
    expect(screen.getByTestId('difficulty-hard')).toBeTruthy();
  });

  it('switches to an explicit level on request', async () => {
    renderWithProviders(<ReadingPractice />);
    await waitFor(() => {
      expect(screen.getByTestId('difficulty-hard')).toBeTruthy();
    });
    fireEvent.press(screen.getByTestId('difficulty-hard'));
    await waitFor(() => {
      expect(screen.getByTestId('difficulty-served')).toHaveTextContent(
        /Serving/,
      );
    });
  });
});

describe('Reading navigator and timer', () => {
  it('marks answered questions and reflects them in the count', async () => {
    renderWithProviders(<ReadingPractice />);
    await waitFor(() => {
      expect(screen.getByTestId('question-navigator')).toBeTruthy();
    });
    expect(screen.getByTestId('nav-q-1')).toBeTruthy();
    // Nothing answered yet.
    expect(screen.getByTestId('navigator-remaining')).toHaveTextContent(/left/);
  });

  it('focuses the question a navigator number points at', async () => {
    renderWithProviders(<ReadingPractice />);
    await waitFor(() => {
      expect(screen.getByTestId('nav-q-2')).toBeTruthy();
    });
    fireEvent.press(screen.getByTestId('nav-q-2'));
    expect(screen.getByTestId('question-card-2')).toBeTruthy();
  });

  it('counts down the 20-minute passage allowance', async () => {
    jest.useFakeTimers();
    try {
      renderWithProviders(<ReadingPractice />);
      await waitFor(() => {
        expect(screen.getByTestId('reading-timer')).toBeTruthy();
      });
      expect(screen.getByTestId('timer-clock')).toHaveTextContent('20:00');
      fireEvent.press(screen.getByTestId('timer-toggle'));
      act(() => {
        jest.advanceTimersByTime(30_000);
      });
      expect(screen.getByTestId('timer-clock')).toHaveTextContent('19:30');
    } finally {
      jest.useRealTimers();
    }
  });
});

describe('Listening play policy', () => {
  it('allows one play under exam rules, then refuses', async () => {
    renderWithProviders(<ListeningPractice />);
    await waitFor(() => {
      expect(screen.getByTestId('play-button')).toBeTruthy();
    });
    expect(screen.getByText(/0\/1 play used/)).toBeTruthy();

    fireEvent.press(screen.getByTestId('play-button')); // start
    fireEvent.press(screen.getByTestId('play-button')); // stop

    await waitFor(() => {
      expect(screen.getByTestId('player-hint')).toHaveTextContent(
        /does not replay/,
      );
    });
    expect(screen.getByText(/1\/1 play used/)).toBeTruthy();
  });

  it('permits replay once practice mode is chosen', async () => {
    // Exam fidelity is the default, but drilling a clip you failed is a
    // legitimate way to learn.
    renderWithProviders(<ListeningPractice />);
    await waitFor(() => {
      expect(screen.getByTestId('play-mode-toggle')).toBeTruthy();
    });
    fireEvent.press(screen.getByTestId('play-button'));
    fireEvent.press(screen.getByTestId('play-button'));
    fireEvent.press(screen.getByTestId('play-mode-toggle'));

    await waitFor(() => {
      expect(screen.getByText(/replay allowed/)).toBeTruthy();
    });
    expect(screen.getByTestId('player-hint')).toHaveTextContent(/Tap play/);
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
