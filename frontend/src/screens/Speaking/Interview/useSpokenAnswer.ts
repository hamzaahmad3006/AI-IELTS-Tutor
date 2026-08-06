/**
 * Joins the recorder to the examiner session: record an answer, upload it.
 *
 * Kept separate from `useExaminerSession` because the two fail for unrelated
 * reasons. A microphone that is blocked and an exam server that is unreachable
 * need different messages and different recovery, and a single hook holding
 * both would flatten them into one "something went wrong".
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  InterviewRecorder,
  MAX_RECORDING_BYTES,
  RecorderError,
  type Recording,
} from '../../../audio/recorder';

/**
 * Below this, a recording is almost certainly a mis-tap rather than an answer.
 * Uploading it would spend a transcription call to be told there were no words.
 */
export const MIN_ANSWER_MS = 700;

export interface SpokenAnswerState {
  isRecording: boolean;
  isUploading: boolean;
  /** Input level from the microphone, for a "we can hear you" indicator. */
  level: number;
  error: string | null;
  startRecording: () => Promise<void>;
  stopAndSend: () => Promise<void>;
  discard: () => Promise<void>;
}

interface Options {
  onAnswer: (file: {
    uri: string;
    name: string;
    type: string;
  }) => Promise<void>;
}

export const useSpokenAnswer = ({ onAnswer }: Options): SpokenAnswerState => {
  const recorder = useRef<InterviewRecorder>(new InterviewRecorder());
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [level, setLevel] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef<boolean>(true);

  useEffect(() => {
    const instance = recorder.current;
    mounted.current = true;
    instance.setLevelListener(value => {
      if (mounted.current) {
        setLevel(value);
      }
    });

    return () => {
      mounted.current = false;
      instance.setLevelListener(undefined);
      // Leaving the microphone open after the screen is gone is both a battery
      // drain and, on Android, a visible recording indicator on a screen the
      // learner has already left.
      void instance.cancel();
    };
  }, []);

  const startRecording = useCallback(async (): Promise<void> => {
    setError(null);
    try {
      await recorder.current.start();
      if (mounted.current) {
        setIsRecording(true);
      }
    } catch (err) {
      if (mounted.current) {
        setError(
          err instanceof RecorderError
            ? err.message
            : 'Could not start recording.',
        );
      }
    }
  }, []);

  const stopAndSend = useCallback(async (): Promise<void> => {
    if (!recorder.current.isRecording) {
      return;
    }

    let recording: Recording;
    try {
      recording = await recorder.current.stop();
    } catch (err) {
      if (mounted.current) {
        setIsRecording(false);
        setError(
          err instanceof Error ? err.message : 'Could not save the recording.',
        );
      }
      return;
    }

    if (mounted.current) {
      setIsRecording(false);
    }

    if (recording.durationMs < MIN_ANSWER_MS) {
      // Discarded locally. Uploading a mis-tap spends a transcription call to
      // be told there were no words in it.
      if (mounted.current) {
        setError(
          'That was too short to send. Hold the button while you speak.',
        );
      }
      return;
    }

    setIsUploading(true);
    try {
      await onAnswer({
        uri: recording.uri,
        name: recording.name,
        type: recording.type,
      });
    } catch (err) {
      if (mounted.current) {
        setError(
          err instanceof Error ? err.message : 'Could not send your answer.',
        );
      }
    } finally {
      if (mounted.current) {
        setIsUploading(false);
      }
    }
  }, [onAnswer]);

  const discard = useCallback(async (): Promise<void> => {
    await recorder.current.cancel();
    if (mounted.current) {
      setIsRecording(false);
      setError(null);
    }
  }, []);

  return {
    isRecording,
    isUploading,
    level,
    error,
    startRecording,
    stopAndSend,
    discard,
  };
};

export { MAX_RECORDING_BYTES };
