/** Progress screen logic: real per-module progress, prediction and weaknesses. */

import { useCallback, useEffect, useState } from 'react';
import { analyticsApi, meApi } from '../../../api';
import type {
  PredictionResponse,
  ProgressResponse,
  WeaknessItem,
} from '../../../types';

interface UseProgressResult {
  progress: ProgressResponse | null;
  prediction: PredictionResponse | null;
  weaknesses: WeaknessItem[];
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

export const useProgress = (): UseProgressResult => {
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [weaknesses, setWeaknesses] = useState<WeaknessItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const [progressData, predictionData, weaknessData] = await Promise.all([
        analyticsApi.getProgress(),
        analyticsApi.getPrediction(),
        meApi.getWeaknesses(),
      ]);
      setProgress(progressData);
      setPrediction(predictionData);
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

  return {
    progress,
    prediction,
    weaknesses,
    isLoading,
    error,
    reload: () => {
      void load();
    },
  };
};
