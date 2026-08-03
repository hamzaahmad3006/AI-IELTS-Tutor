/** Speaking session start: choose the full interview or a single part. */

import { useCallback, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '@models';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export type SessionChoice = 'full' | 'part1' | 'part2' | 'part3';

export interface SessionOption {
  choice: SessionChoice;
  title: string;
  subtitle: string;
  minutes: string;
}

export const SESSION_OPTIONS: SessionOption[] = [
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
  onBack: () => void;
}

export const useSpeakingSession = (): UseSpeakingSessionResult => {
  const navigation = useNavigation<Nav>();
  const [selected, setSelected] = useState<SessionChoice>('full');

  const start = useCallback((): void => {
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
    selected,
    select: setSelected,
    start,
    onBack: () => navigation.goBack(),
  };
};
