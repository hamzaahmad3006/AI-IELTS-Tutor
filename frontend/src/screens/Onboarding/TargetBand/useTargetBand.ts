/** Target-band onboarding step logic. */

import { useCallback } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import {
  nextStep,
  setTargetBand,
  useAppDispatch,
  useAppSelector,
} from '../../../redux';
import type { Band, RootStackParamList } from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UseTargetBandResult {
  step: number;
  totalSteps: number;
  targetBand: Band;
  bandUserLabel: string;
  recommendation: string;
  onChangeBand: (band: Band) => void;
  onNext: () => void;
  onSkip: () => void;
}

const bandToUserLabel = (band: Band): string => {
  if (band >= 8.5) {
    return 'Expert User';
  }
  if (band >= 7.5) {
    return 'Very Good User';
  }
  if (band >= 6.5) {
    return 'Good User';
  }
  if (band >= 5.5) {
    return 'Competent User';
  }
  if (band >= 4.5) {
    return 'Modest User';
  }
  return 'Limited User';
};

export const useTargetBand = (): UseTargetBandResult => {
  const dispatch = useAppDispatch();
  const navigation = useNavigation<Nav>();
  const { step, totalSteps, draft } = useAppSelector(
    (state) => state.onboarding,
  );

  const onChangeBand = useCallback(
    (band: Band): void => {
      dispatch(setTargetBand(band));
    },
    [dispatch],
  );

  const onNext = useCallback((): void => {
    dispatch(nextStep());
    // For the current milestone we route straight into the app shell.
    navigation.reset({ index: 0, routes: [{ name: 'Main' }] });
  }, [dispatch, navigation]);

  const onSkip = useCallback((): void => {
    navigation.reset({ index: 0, routes: [{ name: 'Main' }] });
  }, [navigation]);

  return {
    step,
    totalSteps,
    targetBand: draft.targetBand,
    bandUserLabel: bandToUserLabel(draft.targetBand),
    recommendation:
      "Most top universities require a Band 7.0 or higher. We'll adjust the difficulty of your mock tests to match this target.",
    onChangeBand,
    onNext,
    onSkip,
  };
};
