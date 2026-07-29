/** Grammar lessons logic: library list + inline lesson detail. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { grammarApi } from '../../../api';
import type {
  GrammarLessonDetail,
  GrammarLessonSummary,
  RootStackParamList,
} from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UseGrammarLessonsResult {
  lessons: GrammarLessonSummary[];
  recommendedCount: number;
  selected: GrammarLessonDetail | null;
  isLoading: boolean;
  isLoadingLesson: boolean;
  error: string | null;
  openLesson: (id: string) => void;
  closeLesson: () => void;
  onBack: () => void;
}

export const useGrammarLessons = (): UseGrammarLessonsResult => {
  const navigation = useNavigation<Nav>();
  const [lessons, setLessons] = useState<GrammarLessonSummary[]>([]);
  const [recommendedCount, setRecommendedCount] = useState<number>(0);
  const [selected, setSelected] = useState<GrammarLessonDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLoadingLesson, setIsLoadingLesson] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    grammarApi
      .listLessons()
      .then((data) => {
        if (mounted) {
          setLessons(data.items);
          setRecommendedCount(data.recommendedCount);
        }
      })
      .catch(() => {
        if (mounted) {
          setError('Could not load grammar lessons.');
        }
      })
      .finally(() => {
        if (mounted) {
          setIsLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  const openLesson = useCallback((id: string): void => {
    setIsLoadingLesson(true);
    setError(null);
    grammarApi
      .getLesson(id)
      .then((detail) => setSelected(detail))
      .catch(() => setError('Could not open that lesson.'))
      .finally(() => setIsLoadingLesson(false));
  }, []);

  const closeLesson = useCallback((): void => {
    setSelected(null);
  }, []);

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    lessons,
    recommendedCount,
    selected,
    isLoading,
    isLoadingLesson,
    error,
    openLesson,
    closeLesson,
    onBack,
  };
};
