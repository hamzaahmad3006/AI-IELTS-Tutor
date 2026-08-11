/** Speaking: session start screen and the Part 1 / Part 3 runner. */

import React from 'react';
import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import { SpeakingSession } from '../Speaking/Session/SpeakingSession';
import { SESSION_OPTIONS } from '../Speaking/Session/useSpeakingSession';
import { SpeakingParts } from '../Speaking/Parts/SpeakingParts';
import { renderWithProviders } from '../../testUtils/renderWithProviders';

describe('Speaking session start', () => {
  it('offers the full interview and each part separately', () => {
    renderWithProviders(<SpeakingSession />);
    SESSION_OPTIONS.forEach(option => {
      expect(screen.getByTestId(`session-${option.choice}`)).toBeTruthy();
      expect(screen.getByText(option.title)).toBeTruthy();
    });
  });

  it('defaults to the full interview', () => {
    renderWithProviders(<SpeakingSession />);
    expect(screen.getByTestId('session-full').props.accessibilityState).toEqual(
      expect.objectContaining({ selected: true }),
    );
  });

  it('changes selection when another part is chosen', () => {
    renderWithProviders(<SpeakingSession />);
    fireEvent.press(screen.getByTestId('session-part3'));
    expect(
      screen.getByTestId('session-part3').props.accessibilityState,
    ).toEqual(expect.objectContaining({ selected: true }));
  });

  it('says plainly that answers are typed rather than requesting a mic', () => {
    // Asking for microphone access the app cannot yet use would be worse than
    // stating the limitation up front.
    renderWithProviders(<SpeakingSession />);
    // The session screen must set the expectation before the learner starts:
    // answers are spoken, and the microphone prompt comes at the moment of use.
    expect(screen.getByText(/Record your answers/)).toBeTruthy();
    expect(screen.getByText(/only requested when you tap record/)).toBeTruthy();
  });
});

describe('Speaking Part runner', () => {
  it('shows the first question with part-specific guidance', async () => {
    renderWithProviders(<SpeakingParts />, { routeParams: { part: 1 } });
    await waitFor(() => {
      expect(screen.getByTestId('parts-question-1')).toBeTruthy();
    });
    expect(screen.getByText('QUESTION 1 OF 4')).toBeTruthy();
    expect(screen.getByText('HOW TO ANSWER')).toBeTruthy();
    expect(screen.getByTestId('question-navigator')).toBeTruthy();
  });

  it('keeps Next disabled until the answer is substantial', async () => {
    renderWithProviders(<SpeakingParts />, { routeParams: { part: 1 } });
    await waitFor(() => {
      expect(screen.getByTestId('parts-next')).toBeTruthy();
    });
    // A two-word answer is not an IELTS answer.
    fireEvent.changeText(screen.getByTestId('parts-answer-input'), 'I study');
    expect(screen.getByTestId('parts-next').props.accessibilityState).toEqual(
      expect.objectContaining({ disabled: true }),
    );

    fireEvent.changeText(
      screen.getByTestId('parts-answer-input'),
      'I am a student studying computer science at university here in the city.',
    );
    await waitFor(() => {
      expect(screen.getByTestId('parts-next').props.accessibilityState).toEqual(
        expect.objectContaining({ disabled: false }),
      );
    });
  });

  it('advances through the set and offers scoring at the end', async () => {
    renderWithProviders(<SpeakingParts />, { routeParams: { part: 1 } });
    await waitFor(() => {
      expect(screen.getByTestId('parts-answer-input')).toBeTruthy();
    });

    const answer = 'I am a student studying computer science at a university.';
    for (let i = 0; i < 3; i += 1) {
      fireEvent.changeText(screen.getByTestId('parts-answer-input'), answer);
      await waitFor(() => {
        expect(screen.getByTestId('parts-next')).toBeTruthy();
      });
      fireEvent.press(screen.getByTestId('parts-next'));
    }

    await waitFor(() => {
      expect(screen.getByText('QUESTION 4 OF 4')).toBeTruthy();
    });
    // Last question swaps Next for the scoring action.
    expect(screen.getByTestId('parts-submit')).toBeTruthy();
    expect(screen.queryByTestId('parts-next')).toBeNull();
  });
});
