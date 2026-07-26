/** Home dashboard logic: loads data and exposes navigation handlers. */

import { useCallback, useEffect } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import {
  fetchDashboardThunk,
  useAppDispatch,
  useAppSelector,
} from '../../../redux';
import type {
  DashboardData,
  IeltsModule,
  LoadingStatus,
  RootStackParamList,
} from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UseHomeResult {
  data: DashboardData | null;
  status: LoadingStatus;
  error: string | null;
  onSelectModule: (module: IeltsModule) => void;
  onStartMockTest: () => void;
  reload: () => void;
}

export const useHome = (): UseHomeResult => {
  const dispatch = useAppDispatch();
  const navigation = useNavigation<Nav>();
  const { data, status, error } = useAppSelector((state) => state.dashboard);

  useEffect(() => {
    if (status === 'idle') {
      void dispatch(fetchDashboardThunk());
    }
  }, [dispatch, status]);

  const onSelectModule = useCallback(
    (module: IeltsModule): void => {
      if (module === 'speaking') {
        navigation.navigate('SpeakingInterview', { module });
        return;
      }
      if (module === 'writing') {
        navigation.navigate('WritingPractice');
        return;
      }
      if (module === 'reading') {
        navigation.navigate('ReadingPractice');
        return;
      }
      navigation.navigate('Main', { screen: 'Practice' });
    },
    [navigation],
  );

  const onStartMockTest = useCallback((): void => {
    navigation.navigate('Main', { screen: 'Practice' });
  }, [navigation]);

  const reload = useCallback((): void => {
    void dispatch(fetchDashboardThunk());
  }, [dispatch]);

  return { data, status, error, onSelectModule, onStartMockTest, reload };
};
