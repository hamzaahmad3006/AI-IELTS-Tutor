/** Speaking interview logic: session lifecycle, timer, call controls. */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { speakingApi } from '../../../api';
import type { RootStackParamList, SpeakingSession } from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UseInterviewResult {
  session: SpeakingSession | null;
  isLoading: boolean;
  isMuted: boolean;
  isPaused: boolean;
  elapsedLabel: string;
  toggleMute: () => void;
  togglePause: () => void;
  endCall: () => void;
}

const formatElapsed = (totalSeconds: number): string => {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes.toString().padStart(2, '0')}:${seconds
    .toString()
    .padStart(2, '0')}`;
};

export const useInterview = (): UseInterviewResult => {
  const navigation = useNavigation<Nav>();
  const [session, setSession] = useState<SpeakingSession | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [elapsed, setElapsed] = useState<number>(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let mounted = true;
    const start = async (): Promise<void> => {
      const created = await speakingApi.createSession();
      if (mounted) {
        setSession(created);
        setElapsed(created.elapsedSeconds);
        setIsLoading(false);
      }
    };
    void start();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (isLoading || isPaused) {
      return;
    }
    intervalRef.current = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isLoading, isPaused]);

  const toggleMute = useCallback((): void => {
    setIsMuted((prev) => !prev);
  }, []);

  const togglePause = useCallback((): void => {
    setIsPaused((prev) => !prev);
  }, []);

  const endCall = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    session,
    isLoading,
    isMuted,
    isPaused,
    elapsedLabel: formatElapsed(elapsed),
    toggleMute,
    togglePause,
    endCall,
  };
};
