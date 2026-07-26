/** Speaking practice logic: cue card, response capture, AI scoring.
 *
 * Until the LiveKit voice pipeline lands, the learner's response is captured as
 * text (or a device transcript) and scored through the same AI endpoint the
 * voice interview will use.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { speakingApi } from '../../../api';
import type {
  RootStackParamList,
  SpeakingResult,
  SpeakingPart,
} from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export type SpeakingPhase = 'prep' | 'speaking' | 'scored';

const PREP_SECONDS = 60;
const SPEAK_SECONDS = 120;
const MIN_WORDS = 20;

interface CueCard {
  topic: string;
  prompt: string;
  bullets: string[];
}

const CUE_CARD: CueCard = {
  topic: 'A memorable place',
  prompt: 'Describe a place you visited that made a lasting impression.',
  bullets: [
    'where it was',
    'when you went there',
    'what you did there',
    'and explain why it made a lasting impression',
  ],
};

interface UseSpeakingPracticeResult {
  cueCard: CueCard;
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
  const [phase, setPhase] = useState<SpeakingPhase>('prep');
  const [secondsLeft, setSecondsLeft] = useState<number>(PREP_SECONDS);
  const [transcript, setTranscript] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<SpeakingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const wordCount = useMemo(() => countWords(transcript), [transcript]);

  // Countdown for the active phase (prep or speaking).
  useEffect(() => {
    if (phase === 'scored') {
      return;
    }
    intervalRef.current = setInterval(() => {
      setSecondsLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [phase]);

  const startSpeaking = useCallback((): void => {
    setPhase('speaking');
    setSecondsLeft(SPEAK_SECONDS);
  }, []);

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
        durationSec: SPEAK_SECONDS - secondsLeft,
      })
      .then((res) => {
        setResult(res);
        setPhase('scored');
      })
      .catch(() => setError('Scoring failed. Please try again.'))
      .finally(() => setIsSubmitting(false));
  }, [transcript, wordCount, secondsLeft]);

  const tryAnother = useCallback((): void => {
    setResult(null);
    setTranscript('');
    setError(null);
    setPhase('prep');
    setSecondsLeft(PREP_SECONDS);
  }, []);

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    cueCard: CUE_CARD,
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
    startSpeaking,
    submit,
    tryAnother,
    onBack,
  };
};
