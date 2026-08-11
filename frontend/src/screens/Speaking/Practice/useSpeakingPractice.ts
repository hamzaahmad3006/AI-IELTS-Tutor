/** Speaking practice logic: cue card, response capture, AI scoring.
 *
 * Until the LiveKit voice pipeline lands, the learner's response is captured as
 * text (or a device transcript) and scored through the same AI endpoint the
 * voice interview will use.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { speakingApi } from '@api';
import { t } from '../../../i18n';
import { useSpokenAnswer } from '../Interview/useSpokenAnswer';
import type {
  CueCard,
  RootStackParamList,
  SpeakingResult,
  SpeakingPart,
} from '@models';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export type SpeakingPhase = 'prep' | 'speaking' | 'scored';

const MIN_WORDS = 20;

/** Used until the backend cue card arrives (and if the request fails). */
const FALLBACK_CUE_CARD: CueCard = {
  id: 'fallback',
  topic: 'A memorable place',
  prompt: 'Describe a place you visited that made a lasting impression.',
  bulletPoints: [
    'where it was',
    'when you went there',
    'what you did there',
    'and explain why it made a lasting impression',
  ],
  difficulty: 'medium',
  prepSeconds: 60,
  speakSeconds: 120,
};

interface UseSpeakingPracticeResult {
  cueCard: CueCard;
  /** Live microphone capture for the answer. */
  isRecording: boolean;
  isTranscribing: boolean;
  /** Input level, for a "we can hear you" cue. */
  level: number;
  recordingError: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
  part: SpeakingPart;
  phase: SpeakingPhase;
  secondsLeft: number;
  timerLabel: string;
  transcript: string;
  wordCount: number;
  canSubmit: boolean;
  isSubmitting: boolean;
  result: SpeakingResult | null;
  error: string | null;
  setTranscript: (text: string) => void;
  startSpeaking: () => void;
  submit: () => void;
  tryAnother: () => void;
  onBack: () => void;
}

/** Whatever the API surfaced, or a sentence the learner can act on. */
const toMessage = (error: unknown): string => {
  const detail = error instanceof Error ? error.message : '';
  return detail || t('speaking.transcribeFailed');
};

const countWords = (text: string): number => {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
};

const format = (total: number): string => {
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
};

export const useSpeakingPractice = (): UseSpeakingPracticeResult => {
  const navigation = useNavigation<Nav>();
  const [cueCard, setCueCard] = useState<CueCard>(FALLBACK_CUE_CARD);
  const [phase, setPhase] = useState<SpeakingPhase>('prep');
  const [secondsLeft, setSecondsLeft] = useState<number>(
    FALLBACK_CUE_CARD.prepSeconds,
  );
  const [transcript, setTranscript] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<SpeakingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [isTranscribing, setIsTranscribing] = useState<boolean>(false);
  const [recordingError, setRecordingError] = useState<string | null>(null);

  const wordCount = useMemo(() => countWords(transcript), [transcript]);

  /**
   * Recording reuses the interview's hook rather than a second implementation.
   * The lifecycle problems are identical, and two recorders would be two
   * places to get "stopped when never started" wrong.
   *
   * The transcript is appended rather than replaced, so a candidate can record
   * in several passes -- which is what people actually do when they lose their
   * thread mid-answer.
   */
  const {
    isRecording,
    level,
    error: spokenError,
    startRecording,
    stopAndSend,
  } = useSpokenAnswer({
    onAnswer: async file => {
      setIsTranscribing(true);
      setRecordingError(null);
      try {
        const heard = await speakingApi.transcribe(file);
        if (!heard.isUsable) {
          // Not an error screen: a recogniser that heard nothing is a quiet
          // room or a muted mic, and the answer is still typable.
          setRecordingError(t('speaking.nothingHeard'));
          return;
        }
        setTranscript(previous =>
          previous.trim() ? `${previous.trim()} ${heard.text}` : heard.text,
        );
      } catch (err) {
        setRecordingError(toMessage(err));
      } finally {
        setIsTranscribing(false);
      }
    },
  });

  const loadCueCard = useCallback((): void => {
    speakingApi
      .getCueCard()
      .then(card => {
        setCueCard(card);
        setSecondsLeft(card.prepSeconds);
      })
      .catch(() => {
        // Non-fatal: the fallback cue card keeps practice available.
      });
  }, []);

  useEffect(() => {
    loadCueCard();
  }, [loadCueCard]);

  // Countdown for the active phase (prep or speaking).
  useEffect(() => {
    if (phase === 'scored') {
      return;
    }
    intervalRef.current = setInterval(() => {
      setSecondsLeft(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [phase]);

  const startSpeaking = useCallback((): void => {
    setPhase('speaking');
    setSecondsLeft(cueCard.speakSeconds);
  }, [cueCard.speakSeconds]);

  const submit = useCallback((): void => {
    if (wordCount < MIN_WORDS) {
      setError(`Please give a fuller response (at least ${MIN_WORDS} words).`);
      return;
    }
    setIsSubmitting(true);
    setError(null);
    speakingApi
      .submit({
        transcript,
        part: 2,
        durationSec: Math.max(0, cueCard.speakSeconds - secondsLeft),
      })
      .then(res => {
        setResult(res);
        setPhase('scored');
      })
      .catch(() => setError('Scoring failed. Please try again.'))
      .finally(() => setIsSubmitting(false));
  }, [transcript, wordCount, secondsLeft, cueCard.speakSeconds]);

  const tryAnother = useCallback((): void => {
    setResult(null);
    setTranscript('');
    setError(null);
    setPhase('prep');
    setSecondsLeft(cueCard.prepSeconds);
    loadCueCard();
  }, [cueCard.prepSeconds, loadCueCard]);

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    cueCard,
    part: 2,
    phase,
    secondsLeft,
    timerLabel: format(secondsLeft),
    transcript,
    wordCount,
    canSubmit: wordCount >= MIN_WORDS,
    isSubmitting,
    result,
    error,
    setTranscript,
    isRecording,
    isTranscribing,
    level,
    recordingError: recordingError ?? spokenError,
    startRecording,
    stopRecording: stopAndSend,
    startSpeaking,
    submit,
    tryAnother,
    onBack,
  };
};
