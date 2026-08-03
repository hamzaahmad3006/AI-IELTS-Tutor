/** Onboarding final step: exam type, level, study time, consent, submit. */

import { useCallback, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { profileApi } from '@api';
import {
  resetOnboarding,
  updateDraft,
  useAppDispatch,
  useAppSelector,
} from '@redux';
import type { ExamType, ProficiencyLevel, RootStackParamList } from '@models';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export const STUDY_TIME_OPTIONS = [15, 30, 60, 90] as const;

interface UseExamSetupResult {
  step: number;
  totalSteps: number;
  examType: ExamType;
  selfLevel: ProficiencyLevel;
  dailyMinutes: number;
  consentAi: boolean;
  consentVoice: boolean;
  targetBand: number;
  isSubmitting: boolean;
  error: string | null;
  canSubmit: boolean;
  setExamType: (value: ExamType) => void;
  setSelfLevel: (value: ProficiencyLevel) => void;
  setDailyMinutes: (value: number) => void;
  examDate: string | null;
  dateSheetOpen: boolean;
  openDateSheet: () => void;
  closeDateSheet: () => void;
  setExamDate: (isoDate: string | null) => void;
  toggleConsentAi: () => void;
  toggleConsentVoice: () => void;
  submit: () => void;
  onBack: () => void;
}

export const useExamSetup = (): UseExamSetupResult => {
  const dispatch = useAppDispatch();
  const navigation = useNavigation<Nav>();
  const [dateSheetOpen, setDateSheetOpen] = useState<boolean>(false);
  const { step, totalSteps, draft } = useAppSelector(state => state.onboarding);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const setExamType = useCallback(
    (value: ExamType): void => {
      dispatch(updateDraft({ examType: value }));
    },
    [dispatch],
  );

  const setSelfLevel = useCallback(
    (value: ProficiencyLevel): void => {
      dispatch(updateDraft({ selfLevel: value }));
    },
    [dispatch],
  );

  const setDailyMinutes = useCallback(
    (value: number): void => {
      dispatch(updateDraft({ dailyMinutes: value }));
    },
    [dispatch],
  );

  const toggleConsentAi = useCallback((): void => {
    dispatch(updateDraft({ consentAi: !draft.consentAi }));
  }, [dispatch, draft.consentAi]);

  const toggleConsentVoice = useCallback((): void => {
    dispatch(updateDraft({ consentVoice: !draft.consentVoice }));
  }, [dispatch, draft.consentVoice]);

  const setExamDate = useCallback(
    (isoDate: string | null): void => {
      dispatch(updateDraft({ examDate: isoDate }));
      setDateSheetOpen(false);
    },
    [dispatch],
  );

  const submit = useCallback((): void => {
    if (!draft.consentAi) {
      setError('AI processing consent is required to score your practice.');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    profileApi
      .submitOnboarding({
        examType: draft.examType,
        selfLevel: draft.selfLevel,
        targetBand: draft.targetBand,
        examDate: draft.examDate,
        dailyMinutes: draft.dailyMinutes,
        consentVoice: draft.consentVoice,
        consentAi: draft.consentAi,
      })
      .then(() => {
        dispatch(resetOnboarding());
        navigation.reset({ index: 0, routes: [{ name: 'Main' }] });
      })
      .catch(() => setError('Could not save your plan. Please try again.'))
      .finally(() => setIsSubmitting(false));
  }, [dispatch, draft, navigation]);

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    step,
    totalSteps,
    examType: draft.examType,
    selfLevel: draft.selfLevel,
    dailyMinutes: draft.dailyMinutes,
    consentAi: draft.consentAi,
    consentVoice: draft.consentVoice,
    targetBand: draft.targetBand,
    isSubmitting,
    error,
    canSubmit: draft.consentAi,
    setExamType,
    setSelfLevel,
    setDailyMinutes,
    examDate: draft.examDate,
    dateSheetOpen,
    openDateSheet: () => setDateSheetOpen(true),
    closeDateSheet: () => setDateSheetOpen(false),
    setExamDate,
    toggleConsentAi,
    toggleConsentVoice,
    submit,
    onBack,
  };
};
