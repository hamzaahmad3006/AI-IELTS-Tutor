/**
 * The examiner session hook.
 *
 * What matters here is that the client stays subordinate to the server's state
 * machine: it renders what it is told, it never advances on its own except
 * where the exam clock says to, and it never gets ahead of the exam.
 */

import { act, renderHook, waitFor } from '@testing-library/react-native';
import { interviewApi } from '@api';
import type { InterviewPhase, InterviewSession } from '@models';
import { useExaminerSession } from '../useExaminerSession';

jest.mock('@api', () => ({
  interviewApi: {
    start: jest.fn(),
    get: jest.fn(),
    answer: jest.fn(),
    answerWithAudio: jest.fn(),
    skipPreparation: jest.fn(),
    score: jest.fn(),
  },
}));

const mocked = interviewApi as jest.Mocked<typeof interviewApi>;

const session = (
  phase: InterviewPhase,
  overrides: Partial<InterviewSession['action']> = {},
): InterviewSession => ({
  id: 'sess-1',
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
    phaseIndex: 1,
    phaseCount: 9,
    questionIndex: 0,
    answered: 0,
  },
  isComplete: false,
  speakingAttemptId: null,
});

describe('useExaminerSession', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  it('starts a session and exposes the first instruction', async () => {
    mocked.start.mockResolvedValue(session('greeting'));
    const { result } = renderHook(() => useExaminerSession());

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.session?.phase).toBe('greeting');
    expect(result.current.session?.action.text).toBe('Where do you live?');
    expect(result.current.error).toBeNull();
  });

  it('takes the countdown duration from the server, not from itself', async () => {
    mocked.start.mockResolvedValue(
      session('part2_prep', { kind: 'prepare', durationSeconds: 60 }),
    );
    const { result } = renderHook(() => useExaminerSession());

    await act(async () => {
      await result.current.start();
    });

    // The prep minute is an exam rule. If the client held its own copy the two
    // would drift and the app would stop matching the real test.
    expect(result.current.secondsLeft).toBe(60);
  });

  it('is untimed when the server says so', async () => {
    mocked.start.mockResolvedValue(session('part1'));
    const { result } = renderHook(() => useExaminerSession());

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.secondsLeft).toBeNull();
  });

  it('sends an answer and applies the phase the server returns', async () => {
    mocked.start.mockResolvedValue(session('greeting'));
    mocked.answer.mockResolvedValue(session('part1'));

    const { result } = renderHook(() => useExaminerSession());
    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.answer('My name is Sara.', 'android-device');
    });

    expect(mocked.answer).toHaveBeenCalledWith('sess-1', {
      text: 'My name is Sara.',
      source: 'android-device',
    });
    expect(result.current.session?.phase).toBe('part1');
  });

  it('records where the transcript came from', async () => {
    mocked.start.mockResolvedValue(session('part1'));
    mocked.answer.mockResolvedValue(session('part1'));

    const { result } = renderHook(() => useExaminerSession());
    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.answer('typed out');
    });

    // Defaults to 'typed' rather than claiming a recogniser produced it: this
    // field exists so a poor band can be traced to a poor transcription.
    expect(mocked.answer).toHaveBeenCalledWith('sess-1', {
      text: 'typed out',
      source: 'typed',
    });
  });

  it('does not send a second answer while one is in flight', async () => {
    mocked.start.mockResolvedValue(session('part1'));
    let release: (value: InterviewSession) => void = () => {};
    mocked.answer.mockReturnValue(
      new Promise<InterviewSession>(resolve => {
        release = resolve;
      }),
    );

    const { result } = renderHook(() => useExaminerSession());
    await act(async () => {
      await result.current.start();
    });

    // A double tap, or the countdown firing while a manual submit is running.
    // Without the guard the exam skips a question.
    await act(async () => {
      void result.current.answer('first');
      void result.current.answer('second');
      release(session('part1'));
    });

    expect(mocked.answer).toHaveBeenCalledTimes(1);
  });

  it('re-reads from the server when an answer fails', async () => {
    mocked.start.mockResolvedValue(session('part1'));
    mocked.answer.mockRejectedValue(new Error('Network Error'));
    mocked.get.mockResolvedValue(session('part1'));

    const { result } = renderHook(() => useExaminerSession());
    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.answer('lost in transit');
    });

    expect(result.current.error).toBe('Network Error');
    // The server is the authority on where the exam is. Guessing is how a
    // client ends up a question ahead of the exam it is conducting.
    expect(mocked.get).toHaveBeenCalledWith('sess-1');
  });

  it('keeps the last known state when the re-read also fails', async () => {
    mocked.start.mockResolvedValue(session('part1'));
    mocked.answer.mockRejectedValue(new Error('offline'));
    mocked.get.mockRejectedValue(new Error('still offline'));

    const { result } = renderHook(() => useExaminerSession());
    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.answer('x');
    });

    expect(result.current.session?.phase).toBe('part1');
    expect(result.current.error).toBe('offline');
  });

  it('uploads a recording as an answer', async () => {
    mocked.start.mockResolvedValue(session('part1'));
    mocked.answerWithAudio.mockResolvedValue(session('part1'));

    const { result } = renderHook(() => useExaminerSession());
    await act(async () => {
      await result.current.start();
    });

    const file = { uri: 'file:///a.m4a', name: 'a.m4a', type: 'audio/mp4' };
    await act(async () => {
      await result.current.answerWithAudio(file);
    });

    expect(mocked.answerWithAudio).toHaveBeenCalledWith('sess-1', file);
  });

  it('skips the preparation minute on request', async () => {
    mocked.start.mockResolvedValue(
      session('part2_prep', { kind: 'prepare', durationSeconds: 60 }),
    );
    mocked.skipPreparation.mockResolvedValue(
      session('part2_speaking', { kind: 'long_turn', durationSeconds: 120 }),
    );

    const { result } = renderHook(() => useExaminerSession());
    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.skipPreparation();
    });

    expect(result.current.session?.phase).toBe('part2_speaking');
    // The new phase's own duration replaces the old countdown.
    expect(result.current.secondsLeft).toBe(120);
  });

  it('scores a finished exam', async () => {
    mocked.start.mockResolvedValue(session('scoring'));
    mocked.score.mockResolvedValue({
      attemptId: 'att-1',
      overallBand: 6.5,
    } as never);

    const { result } = renderHook(() => useExaminerSession());
    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.score();
    });

    await waitFor(() => expect(result.current.result).not.toBeNull());
    expect(result.current.result?.overallBand).toBe(6.5);
  });

  it('surfaces a start failure instead of rendering an empty exam', async () => {
    mocked.start.mockRejectedValue(new Error('No cue cards available'));
    const { result } = renderHook(() => useExaminerSession());

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.session).toBeNull();
    expect(result.current.error).toBe('No cue cards available');
    expect(result.current.isLoading).toBe(false);
  });

  it('does nothing before a session exists', async () => {
    const { result } = renderHook(() => useExaminerSession());

    await act(async () => {
      await result.current.answer('into the void');
      await result.current.skipPreparation();
      await result.current.score();
    });

    expect(mocked.answer).not.toHaveBeenCalled();
    expect(mocked.skipPreparation).not.toHaveBeenCalled();
    expect(mocked.score).not.toHaveBeenCalled();
  });
});
