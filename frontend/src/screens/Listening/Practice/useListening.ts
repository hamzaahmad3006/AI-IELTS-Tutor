/** Listening practice logic: load a clip, collect answers, submit for grading. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { listeningApi } from '@api';
import type {
  AnswerMap,
  AnswerValue,
  Difficulty,
  ListeningClip,
  ListeningResult,
  RootStackParamList,
} from '@models';

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
  playMode: PlayMode;
  setPlayMode: (mode: PlayMode) => void;
  playsUsed: number;
  canPlay: boolean;
  togglePlayback: () => void;
  setAnswer: (questionId: string, value: AnswerValue) => void;
  submit: () => void;
  tryAnother: () => void;
  onBack: () => void;
}

export type PlayMode = 'exam' | 'practice';

export const useListening = (): UseListeningResult => {
  const navigation = useNavigation<Nav>();
  const [clip, setClip] = useState<ListeningClip | null>(null);
  const [difficulty, setDifficultyState] = useState<Difficulty>('adaptive');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playMode, setPlayModeState] = useState<PlayMode>('exam');
  const [playsUsed, setPlaysUsed] = useState<number>(0);
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
  // In the real exam the recording plays once and is never repeated, so `exam`
  // is the default. `practice` exists because drilling a clip you failed is a
  // legitimate way to learn, and forcing exam rules on every session would make
  // the feature worse, not more faithful.
  const canPlay = playMode === 'practice' || playsUsed < 1;

  const togglePlayback = useCallback((): void => {
    setIsPlaying(prev => {
      if (prev) {
        return false;
      }
      if (playMode === 'exam' && playsUsed >= 1) {
        return false;
      }
      setPlaysUsed(used => used + 1);
      return true;
    });
  }, [playMode, playsUsed]);

  const setPlayMode = useCallback((mode: PlayMode): void => {
    setPlayModeState(mode);
    // Switching to practice mid-clip must not retroactively grant a replay it
    // had already used, so the counter is only cleared going back to exam.
    if (mode === 'exam') {
      setPlaysUsed(0);
      setIsPlaying(false);
    }
  }, []);

  const setDifficulty = useCallback((value: Difficulty): void => {
    // Answers belong to the old clip, so they are cleared rather than carried
    // onto whatever content the new level returns.
    setDifficultyState(value);
    setAnswers({});
    setResult(null);
    setPlaysUsed(0);
    setIsPlaying(false);
  }, []);

  const setAnswer = useCallback(
    (questionId: string, value: AnswerValue): void => {
      setAnswers(prev => ({ ...prev, [questionId]: value }));
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
      .then(res => setResult(res))
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
    playMode,
    setPlayMode,
    playsUsed,
    canPlay,
    togglePlayback,
    setAnswer,
    submit,
    tryAnother,
    onBack,
  };
};
