/**
 * Drives a spoken interview from the server's examiner state machine.
 *
 * The server owns the exam. This hook renders whatever action it is given and
 * sends back answers; it deliberately holds no rules about phase order, how
 * long preparation lasts, or when the long turn ends. Those all arrive in the
 * action, because a second copy of the exam rules on the client would drift
 * from the first and the app would quietly stop matching the real test.
 *
 * The countdown is the one thing computed locally, for the obvious reason that
 * a per-second server round trip would be absurd. Its *duration* still comes
 * from the server.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { interviewApi } from '@api';
import type {
  InterviewSession,
  SpeakingResult,
  TranscriptSource,
} from '@models';

export interface ExaminerSessionState {
  session: InterviewSession | null;
  result: SpeakingResult | null;
  isLoading: boolean;
  isSubmitting: boolean;
  error: string | null;
  /** Seconds left on a timed phase, or null when the phase is untimed. */
  secondsLeft: number | null;
  start: () => Promise<void>;
  answer: (text: string, source?: TranscriptSource) => Promise<void>;
  answerWithAudio: (file: {
    uri: string;
    name: string;
    type: string;
  }) => Promise<void>;
  skipPreparation: () => Promise<void>;
  score: () => Promise<void>;
}

/** Phases the client advances on its own once the clock runs out. */
const AUTO_ADVANCE_PHASES = new Set(['part2_prep', 'part2_speaking']);

export const useExaminerSession = (): ExaminerSessionState => {
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [result, setResult] = useState<SpeakingResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);

  const mounted = useRef<boolean>(true);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  // Guards against two answers racing: a candidate tapping twice, or the
  // countdown firing while a manual submit is already in flight. Without it
  // the exam skips a question.
  const inFlight = useRef<boolean>(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (timer.current) {
        clearInterval(timer.current);
      }
    };
  }, []);

  const clearTimer = useCallback((): void => {
    if (timer.current) {
      clearInterval(timer.current);
      timer.current = null;
    }
  }, []);

  const apply = useCallback(
    (next: InterviewSession): void => {
      if (!mounted.current) {
        return;
      }
      setSession(next);
      clearTimer();
      setSecondsLeft(next.action.durationSeconds ?? null);
    },
    [clearTimer],
  );

  const describe = (err: unknown): string =>
    err instanceof Error ? err.message : 'Something went wrong';

  const start = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      apply(await interviewApi.start());
      setResult(null);
    } catch (err) {
      if (mounted.current) {
        setError(describe(err));
      }
    } finally {
      if (mounted.current) {
        setIsLoading(false);
      }
    }
  }, [apply]);

  const submit = useCallback(
    async (send: () => Promise<InterviewSession>): Promise<void> => {
      if (!session || inFlight.current) {
        return;
      }
      inFlight.current = true;
      setIsSubmitting(true);
      setError(null);
      try {
        apply(await send());
      } catch (err) {
        if (mounted.current) {
          setError(describe(err));
          // The server is the authority on where the exam is, so on failure we
          // re-read rather than guess. Guessing is how a client ends up a
          // question ahead of the exam it is supposed to be conducting.
          try {
            apply(await interviewApi.get(session.id));
          } catch {
            // Leave the last known state on screen; the retry can be manual.
          }
        }
      } finally {
        inFlight.current = false;
        if (mounted.current) {
          setIsSubmitting(false);
        }
      }
    },
    [apply, session],
  );

  const answer = useCallback(
    async (text: string, source: TranscriptSource = 'typed'): Promise<void> => {
      const current = session;
      if (!current) {
        return;
      }
      await submit(() => interviewApi.answer(current.id, { text, source }));
    },
    [session, submit],
  );

  const answerWithAudio = useCallback(
    async (file: {
      uri: string;
      name: string;
      type: string;
    }): Promise<void> => {
      const current = session;
      if (!current) {
        return;
      }
      await submit(() => interviewApi.answerWithAudio(current.id, file));
    },
    [session, submit],
  );

  const skipPreparation = useCallback(async (): Promise<void> => {
    const current = session;
    if (!current) {
      return;
    }
    await submit(() => interviewApi.skipPreparation(current.id));
  }, [session, submit]);

  const score = useCallback(async (): Promise<void> => {
    const current = session;
    if (!current) {
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      setResult(await interviewApi.score(current.id));
    } catch (err) {
      if (mounted.current) {
        setError(describe(err));
      }
    } finally {
      if (mounted.current) {
        setIsSubmitting(false);
      }
    }
  }, [session]);

  // The countdown. Only the tick is local; the duration came from the server.
  useEffect(() => {
    if (secondsLeft === null || !session || session.isComplete) {
      return;
    }
    if (secondsLeft <= 0) {
      // Timed phases advance on their own: the preparation minute ends whether
      // or not the candidate presses anything, and the long turn is stopped at
      // two minutes because that is what the real examiner does.
      if (AUTO_ADVANCE_PHASES.has(session.phase) && !inFlight.current) {
        void answer('', 'typed');
      }
      return;
    }

    timer.current = setInterval(() => {
      setSecondsLeft(previous =>
        previous === null ? null : Math.max(0, previous - 1),
      );
    }, 1000);

    return () => {
      if (timer.current) {
        clearInterval(timer.current);
        timer.current = null;
      }
    };
  }, [secondsLeft, session, answer]);

  return {
    session,
    result,
    isLoading,
    isSubmitting,
    error,
    secondsLeft,
    start,
    answer,
    answerWithAudio,
    skipPreparation,
    score,
  };
};
