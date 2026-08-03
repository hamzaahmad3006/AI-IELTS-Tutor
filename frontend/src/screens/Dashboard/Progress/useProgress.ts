/** Progress screen logic: real per-module progress, prediction and weaknesses. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { analyticsApi, meApi } from '../../../api';
import type {
  InsightsResponse,
  PredictionResponse,
  ProgressResponse,
  RootStackParamList,
  TrendResponse,
  WeaknessItem,
} from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UseProgressResult {
  progress: ProgressResponse | null;
  prediction: PredictionResponse | null;
  trend: TrendResponse | null;
  insights: InsightsResponse | null;
  weaknesses: WeaknessItem[];
  isLoading: boolean;
  error: string | null;
  reload: () => void;
  openHistory: () => void;
  openPlan: () => void;
}

export const useProgress = (): UseProgressResult => {
  const navigation = useNavigation<Nav>();
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [trend, setTrend] = useState<TrendResponse | null>(null);
  const [insights, setInsights] = useState<InsightsResponse | null>(null);
  const [weaknesses, setWeaknesses] = useState<WeaknessItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const [
        progressData,
        predictionData,
        trendData,
        insightsData,
        weaknessData,
      ] = await Promise.all([
        analyticsApi.getProgress(),
        analyticsApi.getPrediction(),
        analyticsApi.getTrend(),
        analyticsApi.getInsights(),
        meApi.getWeaknesses(),
      ]);
      setProgress(progressData);
      setPrediction(predictionData);
      setTrend(trendData);
      setInsights(insightsData);
      setWeaknesses(weaknessData.items);
    } catch {
      setError('Could not load your progress. Pull to retry.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openHistory = useCallback((): void => {
    navigation.navigate('History');
  }, [navigation]);

  const openPlan = useCallback((): void => {
    navigation.navigate('Plan');
  }, [navigation]);

  return {
    progress,
    prediction,
    trend,
    insights,
    weaknesses,
    isLoading,
    error,
    reload: () => {
      void load();
    },
    openHistory,
    openPlan,
  };
};
