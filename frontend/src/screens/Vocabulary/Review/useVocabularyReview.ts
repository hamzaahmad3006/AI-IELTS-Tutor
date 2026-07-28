/** Vocabulary review logic: flashcard queue, reveal, grade, advance. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { vocabularyApi } from '../../../api';
import type {
  RootStackParamList,
  VocabCard,
  VocabGrade,
  VocabStats,
} from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UseVocabularyReviewResult {
  card: VocabCard | null;
  stats: VocabStats | null;
  position: number;
  total: number;
  isRevealed: boolean;
  isLoading: boolean;
  isFinished: boolean;
  reviewedCount: number;
  error: string | null;
  reveal: () => void;
  grade: (grade: VocabGrade) => void;
  restart: () => void;
  onBack: () => void;
}

export const useVocabularyReview = (): UseVocabularyReviewResult => {
  const navigation = useNavigation<Nav>();
  const [queue, setQueue] = useState<VocabCard[]>([]);
  const [index, setIndex] = useState<number>(0);
  const [isRevealed, setIsRevealed] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [reviewedCount, setReviewedCount] = useState<number>(0);
  const [stats, setStats] = useState<VocabStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const [queueData, statsData] = await Promise.all([
        vocabularyApi.getQueue(10),
        vocabularyApi.getStats(),
      ]);
      setQueue(queueData.items);
      setStats(statsData);
      setIndex(0);
      setIsRevealed(false);
      setReviewedCount(0);
    } catch {
      setError('Could not load your vocabulary session.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const reveal = useCallback((): void => {
    setIsRevealed(true);
  }, []);

  const grade = useCallback(
    (value: VocabGrade): void => {
      const current = queue[index];
      if (!current) {
        return;
      }
      // Advance immediately; grading is recorded in the background so the
      // session stays responsive.
      setIndex((prev) => prev + 1);
      setIsRevealed(false);
      setReviewedCount((prev) => prev + 1);
      vocabularyApi.grade(current.itemId, value).catch(() => {
        setError('A grade could not be saved.');
      });
    },
    [queue, index],
  );

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    card: queue[index] ?? null,
    stats,
    position: Math.min(index + 1, queue.length),
    total: queue.length,
    isRevealed,
    isLoading,
    isFinished: !isLoading && queue.length > 0 && index >= queue.length,
    reviewedCount,
    error,
    reveal,
    grade,
    restart: () => {
      void load();
    },
    onBack,
  };
};
