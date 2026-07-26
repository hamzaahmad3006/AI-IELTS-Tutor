/** Writing practice logic: compose an essay, submit for AI scoring. */

import { useCallback, useMemo, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { writingApi } from '../../../api';
import type { RootStackParamList, WritingResult } from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

const TASK2_PROMPT =
  'Some people believe technology has made our lives more complex, while others ' +
  'think it has simplified them. Discuss both views and give your own opinion. ' +
  'Write at least 250 words.';

const MIN_WORDS = 50;

interface UseWritingResult {
  prompt: string;
  essayText: string;
  wordCount: number;
  canSubmit: boolean;
  isSubmitting: boolean;
  result: WritingResult | null;
  error: string | null;
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
  const [essayText, setEssayText] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<WritingResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wordCount = useMemo(() => countWords(essayText), [essayText]);

  const submit = useCallback((): void => {
    if (wordCount < MIN_WORDS) {
      setError(`Please write at least ${MIN_WORDS} words before submitting.`);
      return;
    }
    setIsSubmitting(true);
    setError(null);
    writingApi
      .submit({ essayText, taskType: 2 })
      .then((res) => setResult(res))
      .catch(() => setError('Scoring failed. Please try again.'))
      .finally(() => setIsSubmitting(false));
  }, [essayText, wordCount]);

  const tryAnother = useCallback((): void => {
    setResult(null);
    setEssayText('');
    setError(null);
  }, []);

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    prompt: TASK2_PROMPT,
    essayText,
    wordCount,
    canSubmit: wordCount >= MIN_WORDS,
    isSubmitting,
    result,
    error,
    setEssay: setEssayText,
    submit,
    tryAnother,
    onBack,
  };
};
