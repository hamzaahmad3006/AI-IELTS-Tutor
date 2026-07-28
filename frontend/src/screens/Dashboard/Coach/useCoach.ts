/** Daily coach logic: recommendations + adaptive difficulty, with routing. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { meApi } from '../../../api';
import type {
  AdaptiveDifficultyItem,
  IeltsModule,
  Recommendation,
  RootStackParamList,
} from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UseCoachResult {
  recommendations: Recommendation[];
  message: string;
  difficulty: AdaptiveDifficultyItem[];
  isLoading: boolean;
  error: string | null;
  reload: () => void;
  openModule: (module: IeltsModule) => void;
  openVocabulary: () => void;
}

export const useCoach = (): UseCoachResult => {
  const navigation = useNavigation<Nav>();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [message, setMessage] = useState<string>('');
  const [difficulty, setDifficulty] = useState<AdaptiveDifficultyItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const [recs, diff] = await Promise.all([
        meApi.getRecommendations(),
        meApi.getAdaptiveDifficulty(),
      ]);
      setRecommendations(recs.items);
      setMessage(recs.message);
      setDifficulty(diff.modules);
    } catch {
      setError('Could not load your coach. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openModule = useCallback(
    (module: IeltsModule): void => {
      switch (module) {
        case 'reading':
          navigation.navigate('ReadingPractice');
          break;
        case 'listening':
          navigation.navigate('ListeningPractice');
          break;
        case 'writing':
          navigation.navigate('WritingPractice');
          break;
        case 'speaking':
          navigation.navigate('SpeakingPractice');
          break;
      }
    },
    [navigation],
  );

  const openVocabulary = useCallback((): void => {
    navigation.navigate('VocabularyReview');
  }, [navigation]);

  return {
    recommendations,
    message,
    difficulty,
    isLoading,
    error,
    reload: () => {
      void load();
    },
    openModule,
    openVocabulary,
  };
};
