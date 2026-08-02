/**
 * Countdown clock shared by the timed practice modules.
 *
 * Lives alongside `useTheme` under components/ rather than in a new top-level
 * folder, matching the existing layout.
 *
 * Expiry never destroys work: it reports `expired` and stops, and it is the
 * screen's job to decide what that means. Auto-submitting or wiping an answer
 * because a practice timer ran out would lose real effort.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export type TimerState = 'idle' | 'running' | 'paused' | 'expired';

/** Amber warning threshold, in seconds remaining. */
export const WARN_AT_SECONDS = 5 * 60;

export interface Countdown {
  secondsLeft: number;
  state: TimerState;
  isWarning: boolean;
  start: () => void;
  pause: () => void;
  reset: () => void;
}

export const useCountdown = (allowanceSeconds: number): Countdown => {
  const [secondsLeft, setSecondsLeft] = useState<number>(allowanceSeconds);
  const [state, setState] = useState<TimerState>('idle');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // A changed allowance means a different task, so the clock is re-armed
  // rather than continuing to count down the previous one.
  useEffect(() => {
    setSecondsLeft(allowanceSeconds);
    setState('idle');
  }, [allowanceSeconds]);

  useEffect(() => {
    if (state !== 'running') {
      return;
    }
    intervalRef.current = setInterval(() => {
      setSecondsLeft((previous) => {
        if (previous <= 1) {
          setState('expired');
          return 0;
        }
        return previous - 1;
      });
    }, 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [state]);

  const start = useCallback((): void => setState('running'), []);
  const pause = useCallback((): void => setState('paused'), []);
  const reset = useCallback((): void => {
    setSecondsLeft(allowanceSeconds);
    setState('idle');
  }, [allowanceSeconds]);

  return {
    secondsLeft,
    state,
    isWarning: state !== 'idle' && secondsLeft <= WARN_AT_SECONDS,
    start,
    pause,
    reset,
  };
};

/** `m:ss`, clamped at zero so a negative never renders. */
export const formatClock = (totalSeconds: number): string => {
  const safe = Math.max(0, totalSeconds);
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, '0')}`;
};
