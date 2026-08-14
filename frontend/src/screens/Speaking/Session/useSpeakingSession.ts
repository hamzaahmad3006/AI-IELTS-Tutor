/** Speaking session start: choose the full interview or a single part. */

import { useCallback, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { interviewApi } from '@api';
import type { RootStackParamList } from '@models';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export type SessionChoice = 'live' | 'full' | 'part1' | 'part2' | 'part3';

export interface SessionOption {
  choice: SessionChoice;
  title: string;
  subtitle: string;
  minutes: string;
}

export const SESSION_OPTIONS: SessionOption[] = [
  {
    // First because it is the one that behaves like a real examiner: it
    // listens over WebRTC and asks its next question from what you said,
    // rather than reading a fixed script.
    choice: 'live',
    title: 'Live AI interview',
    subtitle:
      'Speak with the examiner in real time — it listens and follows up',
    minutes: 'Real-time',
  },
  {
    choice: 'full',
    title: 'Full interview',
    subtitle: 'Parts 1, 2 and 3 back to back, scored as one sitting',
    minutes: '11–14 min',
  },
  {
    choice: 'part1',
    title: 'Part 1 — Introduction',
    subtitle: 'Short questions about familiar, personal topics',
    minutes: '4–5 min',
  },
  {
    choice: 'part2',
    title: 'Part 2 — Long turn',
    subtitle: 'One cue card, one minute to prepare, then speak',
    minutes: '3–4 min',
  },
  {
    choice: 'part3',
    title: 'Part 3 — Discussion',
    subtitle: 'Abstract questions that push you to argue a position',
    minutes: '4–5 min',
  },
];

interface UseSpeakingSessionResult {
  options: SessionOption[];
  selected: SessionChoice;
  select: (choice: SessionChoice) => void;
  start: () => void;
  isStarting: boolean;
  error: string | null;
  onBack: () => void;
}

export const useSpeakingSession = (): UseSpeakingSessionResult => {
  const navigation = useNavigation<Nav>();
  const [selected, setSelected] = useState<SessionChoice>('full');

  const [isStarting, setIsStarting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const start = useCallback((): void => {
    if (selected === 'live') {
      // A session is created first: its id names the LiveKit room, and
      // requesting the token for that room is what starts the examiner.
      setIsStarting(true);
      setError(null);
      interviewApi
        .start()
        .then(session => {
          navigation.navigate('LiveInterview', { sessionId: session.id });
        })
        .catch(() =>
          setError('Could not start the interview. Please try again.'),
        )
        .finally(() => setIsStarting(false));
      return;
    }
    if (selected === 'part2') {
      navigation.navigate('SpeakingPractice');
      return;
    }
    // The full interview begins at Part 1; Part 2 is reached from the run.
    navigation.navigate('SpeakingParts', {
      part: selected === 'part3' ? 3 : 1,
      full: selected === 'full',
    });
  }, [navigation, selected]);

  return {
    options: SESSION_OPTIONS,
    isStarting,
    error,
    selected,
    select: setSelected,
    start,
    onBack: () => navigation.goBack(),
  };
};
