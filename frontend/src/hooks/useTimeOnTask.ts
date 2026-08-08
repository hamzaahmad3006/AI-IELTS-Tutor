/**
 * Measures how long a learner actually spent on a practice screen.
 *
 * The server cannot work this out. It sees one request at the end, and a
 * request timestamp says nothing about whether the learner was working or had
 * the app open in a pocket. So the client measures, and the server clamps what
 * it is told.
 *
 * The measurement stops when the app goes to the background. Without that,
 * every duration is really "time since the screen opened", which for anyone who
 * answers a phone call mid-essay is a wildly wrong number reported with total
 * confidence.
 */

import { useCallback, useEffect, useRef } from 'react';
import { AppState, type AppStateStatus } from 'react-native';

export interface TimeOnTask {
  /** Seconds of foreground time so far. */
  elapsedSeconds: () => number;
  /** Stop counting and return the total. Idempotent. */
  finish: () => number;
  /** Start again from zero, e.g. when the learner retries the exercise. */
  reset: () => void;
}

export const useTimeOnTask = (): TimeOnTask => {
  // Accumulated foreground time from previous stretches, in ms.
  const banked = useRef<number>(0);
  // When the current foreground stretch began, or null while backgrounded.
  const since = useRef<number | null>(Date.now());
  const stopped = useRef<boolean>(false);

  const bank = useCallback((): void => {
    if (since.current !== null) {
      banked.current += Date.now() - since.current;
      since.current = null;
    }
  }, []);

  useEffect(() => {
    const onChange = (state: AppStateStatus): void => {
      if (stopped.current) {
        return;
      }
      if (state === 'active') {
        // Only resume if we are not already counting: 'active' can fire more
        // than once, and resetting the mark each time would discard whatever
        // had accumulated since the last one.
        if (since.current === null) {
          since.current = Date.now();
        }
      } else {
        bank();
      }
    };

    const subscription = AppState.addEventListener('change', onChange);
    return () => {
      subscription.remove();
    };
  }, [bank]);

  const elapsedSeconds = useCallback((): number => {
    const live = since.current === null ? 0 : Date.now() - since.current;
    return Math.round((banked.current + live) / 1000);
  }, []);

  const finish = useCallback((): number => {
    bank();
    stopped.current = true;
    return Math.round(banked.current / 1000);
  }, [bank]);

  const reset = useCallback((): void => {
    banked.current = 0;
    since.current = Date.now();
    stopped.current = false;
  }, []);

  return { elapsedSeconds, finish, reset };
};
