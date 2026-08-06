/**
 * The interview screen.
 *
 * Each exam phase needs different controls, and offering the wrong one is a
 * specific kind of broken: a record button during the silent preparation minute
 * invites the candidate to answer a question they have not been asked, and no
 * record button during Part 1 leaves them with no way to answer at all.
 */

import React from 'react';
import { screen, waitFor } from '@testing-library/react-native';
import { renderWithProviders as render } from '../../../../testUtils/renderWithProviders';
import type { InterviewPhase, InterviewSession } from '@models';
import { ExaminerInterview } from '../ExaminerInterview';

// Every name referenced inside a jest.mock factory must be `mock`-prefixed:
// the factories are hoisted above these declarations.
const mockStart = jest.fn();
const mockAnswer = jest.fn();
const mockSkipPrep = jest.fn();
const mockScore = jest.fn();

// Prefixed with `mock`: jest.mock factories are hoisted above these
// declarations, and only mock-prefixed names are allowed to be referenced.
let mockSession: InterviewSession | null = null;
let mockSecondsLeft: number | null = null;

jest.mock('../useExaminerSession', () => ({
  useExaminerSession: () => ({
    session: mockSession,
    result: null,
    isLoading: false,
    isSubmitting: false,
    error: null,
    secondsLeft: mockSecondsLeft,
    start: mockStart,
    answer: mockAnswer,
    answerWithAudio: jest.fn(),
    skipPreparation: mockSkipPrep,
    score: mockScore,
  }),
}));

jest.mock('../useSpokenAnswer', () => ({
  useSpokenAnswer: () => ({
    isRecording: false,
    isUploading: false,
    level: 0,
    error: null,
    startRecording: jest.fn(),
    stopAndSend: jest.fn(),
    discard: jest.fn(),
  }),
}));

const buildSession = (
  phase: InterviewPhase,
  overrides: Partial<InterviewSession['action']> = {},
): InterviewSession => ({
  id: 's1',
  phase,
  action: {
    kind: 'ask',
    phase,
    text: 'Where do you live?',
    durationSeconds: null,
    bullets: [],
    ...overrides,
  },
  progress: {
    phase,
    phaseIndex: 2,
    phaseCount: 9,
    questionIndex: 0,
    answered: 1,
  },
  isComplete: false,
  speakingAttemptId: null,
});

describe('ExaminerInterview', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSession = null;
    mockSecondsLeft = null;
  });

  it('starts the exam on mount', async () => {
    mockSession = buildSession('part1');
    render(<ExaminerInterview />);
    await waitFor(() => expect(mockStart).toHaveBeenCalledTimes(1));
  });

  it('shows the question and a way to answer it', () => {
    mockSession = buildSession('part1');
    render(<ExaminerInterview />);

    expect(screen.getByText('Where do you live?')).toBeTruthy();
    expect(screen.getByLabelText('Start recording')).toBeTruthy();
    expect(screen.getByText(/Part 1/)).toBeTruthy();
  });

  it('shows the cue card with its bullet points', () => {
    mockSession = buildSession('part2_cue', {
      kind: 'say',
      text: 'Describe a teacher who influenced you.',
      bullets: ['who they were', 'what they taught'],
    });
    render(<ExaminerInterview />);

    expect(screen.getByText(/who they were/)).toBeTruthy();
    expect(screen.getByText(/what they taught/)).toBeTruthy();
    // Nothing to record yet — the examiner is still introducing the task.
    expect(screen.queryByLabelText('Start recording')).toBeNull();
  });

  it('offers no microphone during the silent preparation minute', () => {
    mockSession = buildSession('part2_prep', {
      kind: 'prepare',
      durationSeconds: 60,
    });
    mockSecondsLeft = 60;
    render(<ExaminerInterview />);

    // A record button here would invite the candidate to answer a question
    // they have not been asked yet.
    expect(screen.queryByLabelText('Start recording')).toBeNull();
    expect(screen.getByText('Start speaking now')).toBeTruthy();
    expect(screen.getByText('1:00')).toBeTruthy();
  });

  it('shows the long-turn clock and a microphone', () => {
    mockSession = buildSession('part2_speaking', {
      kind: 'long_turn',
      durationSeconds: 120,
    });
    mockSecondsLeft = 95;
    render(<ExaminerInterview />);

    expect(screen.getByLabelText('Start recording')).toBeTruthy();
    expect(screen.getByText('1:35')).toBeTruthy();
  });

  it('hides the clock on untimed phases', () => {
    mockSession = buildSession('part3');
    mockSecondsLeft = null;
    render(<ExaminerInterview />);

    // A frozen clock reads as a stalled app.
    expect(screen.queryByText(/^\d:\d\d$/)).toBeNull();
  });

  it('asks for the band once the exam reaches scoring', async () => {
    mockSession = buildSession('scoring', {
      kind: 'finish',
      text: 'Thank you.',
    });
    render(<ExaminerInterview />);
    await waitFor(() => expect(mockScore).toHaveBeenCalled());
  });
});
