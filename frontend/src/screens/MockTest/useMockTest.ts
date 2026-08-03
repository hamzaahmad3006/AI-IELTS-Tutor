/** Full mock test: sit four sections against the clock, then read the report. */

import { useCallback, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { mockTestApi } from '../../api';
import { useCountdown, type TimerState } from '../../components';
import type {
  IeltsModule,
  MockResult,
  MockTest,
  RootStackParamList,
} from '../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export type MockStage = 'intro' | 'sitting' | 'result';

interface UseMockTestResult {
  stage: MockStage;
  test: MockTest | null;
  isStarting: boolean;
  isSubmitting: boolean;
  error: string | null;
  sectionIndex: number;
  currentModule: IeltsModule | null;
  isLastSection: boolean;
  readingAnswers: Record<string, string>;
  listeningAnswers: Record<string, string>;
  writingText: string;
  speakingText: string;
  setReadingAnswer: (id: string, value: string) => void;
  setListeningAnswer: (id: string, value: string) => void;
  setWritingText: (text: string) => void;
  setSpeakingText: (text: string) => void;
  secondsLeft: number;
  timerState: TimerState;
  isWarning: boolean;
  startTimer: () => void;
  pauseTimer: () => void;
  resetTimer: () => void;
  start: () => void;
  nextSection: () => void;
  submit: () => void;
  result: MockResult | null;
  onBack: () => void;
}

export const useMockTest = (): UseMockTestResult => {
  const navigation = useNavigation<Nav>();
  const [stage, setStage] = useState<MockStage>('intro');
  const [test, setTest] = useState<MockTest | null>(null);
  const [isStarting, setIsStarting] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [sectionIndex, setSectionIndex] = useState<number>(0);
  const [readingAnswers, setReadingAnswers] = useState<Record<string, string>>({});
  const [listeningAnswers, setListeningAnswers] = useState<Record<string, string>>(
    {},
  );
  const [writingText, setWritingText] = useState<string>('');
  const [speakingText, setSpeakingText] = useState<string>('');
  const [result, setResult] = useState<MockResult | null>(null);

  const section = test?.sections[sectionIndex] ?? null;
  // Each section carries its own real allowance, so the clock is re-armed per
  // section rather than running one budget across the whole sitting.
  const countdown = useCountdown((section?.minutes ?? 30) * 60);

  const start = useCallback((): void => {
    setIsStarting(true);
    setError(null);
    mockTestApi
      .start()
      .then((data) => {
        setTest(data);
        setSectionIndex(0);
        setStage('sitting');
      })
      .catch(() => setError('Could not start a mock test.'))
      .finally(() => setIsStarting(false));
  }, []);

  const submit = useCallback((): void => {
    if (!test) {
      return;
    }
    setIsSubmitting(true);
    setError(null);
    mockTestApi
      .submit(test.id, {
        readingAnswers,
        listeningAnswers,
        // Blank means not attempted, which the report names explicitly rather
        // than folding a zero into the overall.
        writingText: writingText.trim() || null,
        speakingText: speakingText.trim() || null,
      })
      .then((data) => {
        setResult(data);
        setStage('result');
      })
      .catch(() => setError('Could not score the mock test.'))
      .finally(() => setIsSubmitting(false));
  }, [test, readingAnswers, listeningAnswers, writingText, speakingText]);

  const isLastSection = test ? sectionIndex >= test.sections.length - 1 : false;

  const nextSection = useCallback((): void => {
    if (isLastSection) {
      submit();
      return;
    }
    setSectionIndex((i) => i + 1);
    countdown.reset();
  }, [isLastSection, submit, countdown]);

  return {
    stage,
    test,
    isStarting,
    isSubmitting,
    error,
    sectionIndex,
    currentModule: section?.module ?? null,
    isLastSection,
    readingAnswers,
    listeningAnswers,
    writingText,
    speakingText,
    setReadingAnswer: (id, value) =>
      setReadingAnswers((prev) => ({ ...prev, [id]: value })),
    setListeningAnswer: (id, value) =>
      setListeningAnswers((prev) => ({ ...prev, [id]: value })),
    setWritingText,
    setSpeakingText,
    secondsLeft: countdown.secondsLeft,
    timerState: countdown.state,
    isWarning: countdown.isWarning,
    startTimer: countdown.start,
    pauseTimer: countdown.pause,
    resetTimer: countdown.reset,
    start,
    nextSection,
    submit,
    result,
    onBack: () => navigation.goBack(),
  };
};
