/** Listening practice logic: load a clip, collect answers, submit for grading. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { listeningApi } from '../../../api';
import type {
  AnswerMap,
  AnswerValue,
  Difficulty,
  ListeningClip,
  ListeningResult,
  RootStackParamList,
} from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UseListeningResult {
  clip: ListeningClip | null;
  isLoading: boolean;
  answers: AnswerMap;
  answeredCount: number;
  isPlaying: boolean;
  isSubmitting: boolean;
  result: ListeningResult | null;
  error: string | null;
  difficulty: Difficulty;
  setDifficulty: (value: Difficulty) => void;
  togglePlayback: () => void;
  setAnswer: (questionId: string, value: AnswerValue) => void;
  submit: () => void;
  tryAnother: () => void;
  onBack: () => void;
}

export const useListening = (): UseListeningResult => {
  const navigation = useNavigation<Nav>();
  const [clip, setClip] = useState<ListeningClip | null>(null);
  const [difficulty, setDifficultyState] = useState<Difficulty>('adaptive');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<ListeningResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadClip = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listeningApi.getClip(
        difficulty === 'adaptive' ? undefined : difficulty,
      );
      setClip(data);
    } catch {
      setError('Could not load audio. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [difficulty]);

  useEffect(() => {
    void loadClip();
  }, [loadClip]);

  /**
   * Playback state only. Native audio playback lands with the media player
   * integration; the transcript-based questions are answerable meanwhile.
   */
  const togglePlayback = useCallback((): void => {
    setIsPlaying((prev) => !prev);
  }, []);

  const setDifficulty = useCallback((value: Difficulty): void => {
    // Answers belong to the old clip, so they are cleared rather than carried
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
    if (!clip) {
      return;
    }
    setIsSubmitting(true);
    setError(null);
    listeningApi
      .submit({ audioId: clip.id, answers })
      .then((res) => setResult(res))
      .catch(() => setError('Submission failed. Please try again.'))
      .finally(() => setIsSubmitting(false));
  }, [clip, answers]);

  const tryAnother = useCallback((): void => {
    setResult(null);
    setAnswers({});
    setIsPlaying(false);
    void loadClip();
  }, [loadClip]);

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    clip,
    isLoading,
    answers,
    answeredCount: Object.keys(answers).length,
    isPlaying,
    isSubmitting,
    result,
    error,
    difficulty,
    setDifficulty,
    togglePlayback,
    setAnswer,
    submit,
    tryAnother,
    onBack,
  };
};
