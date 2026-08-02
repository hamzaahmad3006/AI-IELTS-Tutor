/** Placement diagnostic: step through four short sections, then show results. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { diagnosticApi } from '../../../api';
import type {
  DiagnosticResult,
  DiagnosticSet,
  OnboardingStackParamList,
} from '../../../types';

type Nav = NativeStackNavigationProp<OnboardingStackParamList>;

export type DiagnosticStep = 'reading' | 'listening' | 'writing' | 'speaking';

export const STEPS: DiagnosticStep[] = [
  'reading',
  'listening',
  'writing',
  'speaking',
];

export const STEP_LABELS: Record<DiagnosticStep, string> = {
  reading: 'Reading',
  listening: 'Listening',
  writing: 'Writing',
  speaking: 'Speaking',
};

interface UseDiagnosticResult {
  set: DiagnosticSet | null;
  isLoading: boolean;
  error: string | null;
  step: DiagnosticStep;
  stepIndex: number;
  totalSteps: number;
  isLastStep: boolean;
  readingAnswers: Record<string, string>;
  listeningAnswers: Record<string, string>;
  writingText: string;
  speakingText: string;
  setReadingAnswer: (questionId: string, value: string) => void;
  setListeningAnswer: (questionId: string, value: string) => void;
  setWritingText: (text: string) => void;
  setSpeakingText: (text: string) => void;
  next: () => void;
  back: () => void;
  isSubmitting: boolean;
  result: DiagnosticResult | null;
  submit: () => void;
  finish: () => void;
}

export const useDiagnostic = (): UseDiagnosticResult => {
  const navigation = useNavigation<Nav>();
  const [set, setSet] = useState<DiagnosticSet | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState<number>(0);
  const [readingAnswers, setReadingAnswers] = useState<Record<string, string>>({});
  const [listeningAnswers, setListeningAnswers] = useState<Record<string, string>>(
    {},
  );
  const [writingText, setWritingText] = useState<string>('');
  const [speakingText, setSpeakingText] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<DiagnosticResult | null>(null);

  useEffect(() => {
    let active = true;
    diagnosticApi
      .getSet()
      .then((data) => {
        if (active) {
          setSet(data);
        }
      })
      .catch(() => {
        if (active) {
          setError('Could not load the placement test. You can skip it for now.');
        }
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const submit = useCallback((): void => {
    setIsSubmitting(true);
    setError(null);
    diagnosticApi
      .submit({
        readingAnswers,
        listeningAnswers,
        // Blank means "not attempted", which the API reports as no estimate
        // rather than a band of zero.
        writingText: writingText.trim() || null,
        speakingText: speakingText.trim() || null,
      })
      .then((data) => setResult(data))
      .catch(() => setError('Could not score the placement test.'))
      .finally(() => setIsSubmitting(false));
  }, [readingAnswers, listeningAnswers, writingText, speakingText]);

  const finish = useCallback((): void => {
    navigation.replace('TargetBand');
  }, [navigation]);

  return {
    set,
    isLoading,
    error,
    step: STEPS[stepIndex],
    stepIndex,
    totalSteps: STEPS.length,
    isLastStep: stepIndex === STEPS.length - 1,
    readingAnswers,
    listeningAnswers,
    writingText,
    speakingText,
    setReadingAnswer: (questionId, value) =>
      setReadingAnswers((prev) => ({ ...prev, [questionId]: value })),
    setListeningAnswer: (questionId, value) =>
      setListeningAnswers((prev) => ({ ...prev, [questionId]: value })),
    setWritingText,
    setSpeakingText,
    next: () => setStepIndex((i) => Math.min(STEPS.length - 1, i + 1)),
    back: () => setStepIndex((i) => Math.max(0, i - 1)),
    isSubmitting,
    result,
    submit,
    finish,
  };
};
