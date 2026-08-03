/** Writing practice logic: pick a task, write against the clock, submit. */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { writingApi } from '@api';
import { useCountdown, type TimerState } from '@components';
import type {
  ExamType,
  RootStackParamList,
  WritingPrompt,
  WritingResult,
} from '@models';

type Nav = NativeStackNavigationProp<RootStackParamList>;

const FALLBACK_PROMPT =
  'Some people believe technology has made our lives more complex, while others ' +
  'think it has simplified them. Discuss both views and give your own opinion.';

/** Minimum words before submitting (kept low so practice is never blocked). */
const MIN_WORDS = 50;

/** Real IELTS allowances: 20 minutes for Task 1, 40 for Task 2. */
export const TASK_MINUTES: Record<number, number> = { 1: 20, 2: 40 };

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
  const countdown = useCountdown(allowanceSeconds);

  const loadPrompt = useCallback((): void => {
    writingApi
      .getPrompt(taskNumber, examType)
      .then(data => setPrompt(data))
      .catch(() => {
        // Non-fatal: fall back to a built-in prompt so practice still works.
      });
  }, [taskNumber, examType]);

  useEffect(() => {
    loadPrompt();
  }, [loadPrompt]);

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

  const submit = useCallback((): void => {
    if (wordCount < MIN_WORDS) {
      setError(`Please write at least ${MIN_WORDS} words before submitting.`);
      return;
    }
    setIsSubmitting(true);
    setError(null);
    if (countdown.state === 'running') {
      countdown.pause();
    }
    writingApi
      .submit({
        essayText,
        taskType: prompt?.taskNumber ?? taskNumber,
        promptText: prompt?.prompt,
      })
      .then(res => setResult(res))
      .catch(() => setError('Scoring failed. Please try again.'))
      .finally(() => setIsSubmitting(false));
  }, [essayText, wordCount, prompt, taskNumber, countdown]);

  const tryAnother = useCallback((): void => {
    setResult(null);
    setEssayText('');
    setError(null);
    countdown.reset();
    loadPrompt();
  }, [loadPrompt, countdown]);

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
    secondsLeft: countdown.secondsLeft,
    timerState: countdown.state,
    isWarning: countdown.isWarning,
    startTimer: countdown.start,
    pauseTimer: countdown.pause,
    resetTimer: countdown.reset,
    setEssay: setEssayText,
    submit,
    tryAnother,
    onBack,
  };
};
