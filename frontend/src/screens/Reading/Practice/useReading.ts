/** Reading practice logic: load a passage, collect answers, submit for grading. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { readingApi } from '../../../api';
import type {
  AnswerMap,
  AnswerValue,
  Difficulty,
  ReadingPassage,
  ReadingResult,
  RootStackParamList,
} from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UseReadingResult {
  passage: ReadingPassage | null;
  isLoading: boolean;
  answers: AnswerMap;
  answeredCount: number;
  isSubmitting: boolean;
  result: ReadingResult | null;
  error: string | null;
  difficulty: Difficulty;
  setDifficulty: (value: Difficulty) => void;
  setAnswer: (questionId: string, value: AnswerValue) => void;
  submit: () => void;
  tryAnother: () => void;
  onBack: () => void;
}

export const useReading = (): UseReadingResult => {
  const navigation = useNavigation<Nav>();
  const [passage, setPassage] = useState<ReadingPassage | null>(null);
  const [difficulty, setDifficultyState] = useState<Difficulty>('adaptive');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<ReadingResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadPassage = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await readingApi.getPassage(
        difficulty === 'adaptive' ? undefined : difficulty,
      );
      setPassage(data);
    } catch {
      setError('Could not load a passage. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [difficulty]);

  useEffect(() => {
    void loadPassage();
  }, [loadPassage]);

  const setDifficulty = useCallback((value: Difficulty): void => {
    // Answers belong to the old item, so they are cleared rather than carried
    // onto whatever content the new level returns.
    setDifficultyState(value);
    setAnswers({});
    setResult(null);
  }, []);

  const setAnswer = useCallback(
    (questionId: string, value: AnswerValue): void => {
      setAnswers((prev) => ({ ...prev, [questionId]: value }));
    },
    [],
  );

  const submit = useCallback((): void => {
    if (!passage) {
      return;
    }
    setIsSubmitting(true);
    setError(null);
    readingApi
      .submit({ passageId: passage.id, answers })
      .then((res) => setResult(res))
      .catch(() => setError('Submission failed. Please try again.'))
      .finally(() => setIsSubmitting(false));
  }, [passage, answers]);

  const tryAnother = useCallback((): void => {
    setResult(null);
    setAnswers({});
    void loadPassage();
  }, [loadPassage]);

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    passage,
    isLoading,
    answers,
    answeredCount: Object.keys(answers).length,
    isSubmitting,
    result,
    error,
    difficulty,
    setDifficulty,
    setAnswer,
    submit,
    tryAnother,
    onBack,
  };
};
