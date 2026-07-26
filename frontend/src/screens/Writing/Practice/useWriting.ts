/** Writing practice logic: compose an essay, submit for AI scoring. */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { writingApi } from '../../../api';
import type {
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
  const [prompt, setPrompt] = useState<WritingPrompt | null>(null);
  const [essayText, setEssayText] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<WritingResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadPrompt = useCallback((): void => {
    writingApi
      .getPrompt(2)
      .then((data) => setPrompt(data))
      .catch(() => {
        // Non-fatal: fall back to a built-in prompt so practice still works.
      });
  }, []);

  useEffect(() => {
    loadPrompt();
  }, [loadPrompt]);

  const wordCount = useMemo(() => countWords(essayText), [essayText]);

  const submit = useCallback((): void => {
    if (wordCount < MIN_WORDS) {
      setError(`Please write at least ${MIN_WORDS} words before submitting.`);
      return;
    }
    setIsSubmitting(true);
    setError(null);
    writingApi
      .submit({
        essayText,
        taskType: prompt?.taskNumber ?? 2,
        promptText: prompt?.prompt,
      })
      .then((res) => setResult(res))
      .catch(() => setError('Scoring failed. Please try again.'))
      .finally(() => setIsSubmitting(false));
  }, [essayText, wordCount, prompt]);

  const tryAnother = useCallback((): void => {
    setResult(null);
    setEssayText('');
    setError(null);
    loadPrompt();
  }, [loadPrompt]);

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    prompt: prompt?.prompt ?? FALLBACK_PROMPT,
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
