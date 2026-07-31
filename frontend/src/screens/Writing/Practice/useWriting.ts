/** Writing practice logic: pick a task, write against the clock, submit. */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { writingApi } from '../../../api';
import type {
  ExamType,
  RootStackParamList,
  WritingPrompt,
  WritingResult,
} from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

const FALLBACK_PROMPT =
  'Some people believe technology has made our lives more complex, while others ' +
  'think it has simplified them. Discuss both views and give your own opinion.';

/** Minimum words before submitting (kept low so practice is never blocked). */
const MIN_WORDS = 50;

/** Real IELTS allowances: 20 minutes for Task 1, 40 for Task 2. */
export const TASK_MINUTES: Record<number, number> = { 1: 20, 2: 40 };

/** Amber warning threshold, in seconds remaining. */
export const WARN_AT_SECONDS = 5 * 60;

export type TimerState = 'idle' | 'running' | 'paused' | 'expired';

interface UseWritingResult {
  prompt: string;
  minWords: number;
  examType: ExamType;
  taskNumber: number;
  setExamType: (examType: ExamType) => void;
  setTaskNumber: (taskNumber: number) => void;
  essayText: string;
  wordCount: number;
  canSubmit: boolean;
  isSubmitting: boolean;
  result: WritingResult | null;
  error: string | null;
  secondsLeft: number;
  timerState: TimerState;
  isWarning: boolean;
  startTimer: () => void;
  pauseTimer: () => void;
  resetTimer: () => void;
  setEssay: (text: string) => void;
  submit: () => void;
  tryAnother: () => void;
  onBack: () => void;
}

const countWords = (text: string): number => {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
};

export const useWriting = (): UseWritingResult => {
  const navigation = useNavigation<Nav>();
  const [prompt, setPrompt] = useState<WritingPrompt | null>(null);
  const [examType, setExamTypeState] = useState<ExamType>('academic');
  const [taskNumber, setTaskNumberState] = useState<number>(2);
  const [essayText, setEssayText] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<WritingResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const allowanceSeconds = (TASK_MINUTES[taskNumber] ?? 40) * 60;
  const [secondsLeft, setSecondsLeft] = useState<number>(allowanceSeconds);
  const [timerState, setTimerState] = useState<TimerState>('idle');

  const loadPrompt = useCallback((): void => {
    writingApi
      .getPrompt(taskNumber, examType)
      .then((data) => setPrompt(data))
      .catch(() => {
        // Non-fatal: fall back to a built-in prompt so practice still works.
      });
  }, [taskNumber, examType]);

  useEffect(() => {
    loadPrompt();
  }, [loadPrompt]);

  // Switching paper changes the allowance, so the clock has to be re-armed.
  useEffect(() => {
    setSecondsLeft(allowanceSeconds);
    setTimerState('idle');
  }, [allowanceSeconds]);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (timerState !== 'running') {
      return;
    }
    intervalRef.current = setInterval(() => {
      setSecondsLeft((previous) => {
        if (previous <= 1) {
          // Time is up, but the essay is never discarded or force-submitted.
          // Losing someone's work to a practice timer is indefensible; the UI
          // just stops pretending there is time left.
          setTimerState('expired');
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
  }, [timerState]);

  const wordCount = useMemo(() => countWords(essayText), [essayText]);
  const minWords = prompt?.minWords ?? (taskNumber === 1 ? 150 : 250);

  const setExamType = useCallback((next: ExamType): void => {
    setExamTypeState(next);
    setEssayText('');
    setError(null);
  }, []);

  const setTaskNumber = useCallback((next: number): void => {
    setTaskNumberState(next);
    setEssayText('');
    setError(null);
  }, []);

  const startTimer = useCallback((): void => setTimerState('running'), []);
  const pauseTimer = useCallback((): void => setTimerState('paused'), []);
  const resetTimer = useCallback((): void => {
    setSecondsLeft(allowanceSeconds);
    setTimerState('idle');
  }, [allowanceSeconds]);

  const submit = useCallback((): void => {
    if (wordCount < MIN_WORDS) {
      setError(`Please write at least ${MIN_WORDS} words before submitting.`);
      return;
    }
    setIsSubmitting(true);
    setError(null);
    setTimerState((state) => (state === 'running' ? 'paused' : state));
    writingApi
      .submit({
        essayText,
        taskType: prompt?.taskNumber ?? taskNumber,
        promptText: prompt?.prompt,
      })
      .then((res) => setResult(res))
      .catch(() => setError('Scoring failed. Please try again.'))
      .finally(() => setIsSubmitting(false));
  }, [essayText, wordCount, prompt, taskNumber]);

  const tryAnother = useCallback((): void => {
    setResult(null);
    setEssayText('');
    setError(null);
    setSecondsLeft(allowanceSeconds);
    setTimerState('idle');
    loadPrompt();
  }, [loadPrompt, allowanceSeconds]);

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    prompt: prompt?.prompt ?? FALLBACK_PROMPT,
    minWords,
    examType,
    taskNumber,
    setExamType,
    setTaskNumber,
    essayText,
    wordCount,
    canSubmit: wordCount >= MIN_WORDS,
    isSubmitting,
    result,
    error,
    secondsLeft,
    timerState,
    isWarning: timerState !== 'idle' && secondsLeft <= WARN_AT_SECONDS,
    startTimer,
    pauseTimer,
    resetTimer,
    setEssay: setEssayText,
    submit,
    tryAnother,
    onBack,
  };
};
