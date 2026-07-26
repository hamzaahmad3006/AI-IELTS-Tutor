/** Practice hub logic: module launcher with each module's adaptive level. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { meApi } from '../../../api';
import type {
  AdaptiveDifficultyItem,
  IeltsModule,
  RootStackParamList,
} from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UsePracticeResult {
  difficultyByModule: Record<string, AdaptiveDifficultyItem>;
  isLoading: boolean;
  openModule: (module: IeltsModule) => void;
}

export const usePractice = (): UsePracticeResult => {
  const navigation = useNavigation<Nav>();
  const [difficultyByModule, setDifficultyByModule] = useState<
    Record<string, AdaptiveDifficultyItem>
  >({});
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    meApi
      .getAdaptiveDifficulty()
      .then((res) => {
        if (!mounted) {
          return;
        }
        const map: Record<string, AdaptiveDifficultyItem> = {};
        res.modules.forEach((item) => {
          map[item.module] = item;
        });
        setDifficultyByModule(map);
      })
      .catch(() => {
        // Non-fatal: the hub still launches modules without level badges.
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

  return { difficultyByModule, isLoading, openModule };
};
