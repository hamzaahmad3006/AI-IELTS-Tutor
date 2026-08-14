/**
 * The live voice interview: join the room, publish the microphone, listen.
 *
 * Everything audible happens on the other side of the room -- the examiner is
 * a worker process that joins the same LiveKit room, hears the candidate over
 * WebRTC, and speaks back on its own track. This hook's whole job is to get
 * connected, keep the microphone published, and surface enough state that the
 * screen is not a silent rectangle.
 *
 * The examiner's audio needs no handling here. LiveKit plays remote audio
 * tracks through the device's audio session automatically once subscribed;
 * trying to route it manually is how you end up with it playing twice.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { interviewApi } from '@api';
import { requestMicrophonePermission } from '../../../audio/recorder';
import { t } from '../../../i18n';
import {
  InterviewRoom,
  type ExamState,
  type RoomStatus,
} from '../../../voice/liveKitRoom';

export type Phase =
  | 'idle'
  | 'connecting'
  | 'waiting'
  | 'examinerSpeaking'
  | 'listening'
  | 'thinking'
  | 'finished'
  | 'failed';

export interface LiveInterviewState {
  phase: Phase;
  status: RoomStatus;
  /** What the examiner just said, so the demo is readable without audio. */
  examinerText: string;
  /** What we heard back, shown once the turn ends. */
  lastAnswer: string;
  error: string | null;
  isMuted: boolean;
  start: () => Promise<void>;
  end: () => Promise<void>;
  toggleMute: () => Promise<void>;
}

/** Map the agent's state frames onto the phase the screen renders. */
const phaseFor = (state: ExamState, current: Phase): Phase => {
  if (state.finished) {
    return 'finished';
  }
  if (state.speaking) {
    return 'examinerSpeaking';
  }
  if (state.thinking) {
    return 'thinking';
  }
  if (state.listening) {
    return 'listening';
  }
  // A frame that says only "not speaking" arrives at the end of every
  // examiner turn; keeping the current phase stops the UI flickering back to
  // "waiting" between every question.
  return current === 'connecting' ? 'waiting' : current;
};

export const useLiveInterview = (sessionId: string): LiveInterviewState => {
  const room = useRef<InterviewRoom>(new InterviewRoom());
  const [phase, setPhase] = useState<Phase>('idle');
  const [status, setStatus] = useState<RoomStatus>('idle');
  const [examinerText, setExaminerText] = useState<string>('');
  const [lastAnswer, setLastAnswer] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const mounted = useRef<boolean>(true);

  useEffect(() => {
    const instance = room.current;
    mounted.current = true;
    return () => {
      mounted.current = false;
      // A room left connected holds the microphone for the whole app, and the
      // next screen that wants it fails with no obvious cause.
      void instance.disconnect();
    };
  }, []);

  const start = useCallback(async (): Promise<void> => {
    setError(null);
    setPhase('connecting');

    // Asked before the token, so a refusal costs nothing and the learner is
    // not left in a room they cannot speak in.
    const permission = await requestMicrophonePermission();
    if (permission !== 'granted') {
      setPhase('failed');
      setError(
        permission === 'blocked'
          ? t('error.microphoneBlocked')
          : t('error.microphoneNeeded'),
      );
      return;
    }

    try {
      // Issuing the token is also what starts the examiner worker, so this
      // call is what makes the room have someone in it.
      const credentials = await interviewApi.realtimeToken(sessionId);

      await room.current.connect(credentials.url, credentials.token, {
        onStatus: next => {
          if (!mounted.current) {
            return;
          }
          setStatus(next);
          if (next === 'disconnected') {
            setPhase(previous =>
              previous === 'finished' ? previous : 'failed',
            );
          }
        },
        onExamState: state => {
          if (!mounted.current) {
            return;
          }
          if (state.text) {
            setExaminerText(state.text);
          }
          if (state.transcript) {
            setLastAnswer(state.transcript);
          }
          setPhase(previous => phaseFor(state, previous));
        },
      });

      if (mounted.current) {
        // Connected, but the examiner has not spoken yet: it waits for our
        // audio track before greeting, so an empty room is never talked to.
        setPhase(previous =>
          previous === 'connecting' ? 'waiting' : previous,
        );
      }
    } catch (err) {
      if (!mounted.current) {
        return;
      }
      setPhase('failed');
      setError(
        (err as Error).message ||
          'Could not start the interview. Please try again.',
      );
    }
  }, [sessionId]);

  const end = useCallback(async (): Promise<void> => {
    await room.current.disconnect();
    if (mounted.current) {
      setPhase('finished');
    }
  }, []);

  const toggleMute = useCallback(async (): Promise<void> => {
    const next = !isMuted;
    await room.current.setMicrophoneEnabled(!next);
    if (mounted.current) {
      setIsMuted(next);
    }
  }, [isMuted]);

  return {
    phase,
    status,
    examinerText,
    lastAnswer,
    error,
    isMuted,
    start,
    end,
    toggleMute,
  };
};
