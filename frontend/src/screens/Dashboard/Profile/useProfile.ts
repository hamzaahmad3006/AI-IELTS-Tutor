/** Profile & settings logic: real profile, editable goals, theme, logout. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Share } from 'react-native';
import { meApi, plannerApi, profileApi } from '@api';
import {
  logout,
  logoutThunk,
  showToast,
  toggleTheme,
  useAppDispatch,
  useAppSelector,
} from '@redux';
import type { ConsentValues } from '@components';
import type {
  AuthenticatedUser,
  Band,
  ProfileResponse,
  RootStackParamList,
} from '@models';
import type { ThemeMode } from '@constants';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UseProfileResult {
  user: AuthenticatedUser | null;
  profile: ProfileResponse | null;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  themeMode: ThemeMode;
  onChangeTargetBand: (band: Band) => void;
  onChangeDailyMinutes: (minutes: number) => void;
  consentSheetOpen: boolean;
  openConsentSheet: () => void;
  closeConsentSheet: () => void;
  onSaveConsent: (next: ConsentValues) => void;
  dateSheetOpen: boolean;
  openDateSheet: () => void;
  closeDateSheet: () => void;
  onChangeExamDate: (isoDate: string | null) => void;
  isExporting: boolean;
  onExportData: () => void;
  deleteSheetOpen: boolean;
  openDeleteSheet: () => void;
  closeDeleteSheet: () => void;
  isDeleting: boolean;
  onDeleteAccount: () => void;
  onToggleTheme: () => void;
  onLogout: () => void;
}

export const useProfile = (): UseProfileResult => {
  const dispatch = useAppDispatch();
  const navigation = useNavigation<Nav>();
  const user = useAppSelector(state => state.auth.user);
  const themeMode = useAppSelector(state => state.theme.mode);
  const refreshToken = useAppSelector(state => state.auth.tokens?.refreshToken);

  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [consentSheetOpen, setConsentSheetOpen] = useState<boolean>(false);
  const [dateSheetOpen, setDateSheetOpen] = useState<boolean>(false);
  const [deleteSheetOpen, setDeleteSheetOpen] = useState<boolean>(false);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;
    profileApi
      .getProfile()
      .then(data => {
        if (mounted) {
          setProfile(data);
        }
      })
      .catch(() => {
        // A learner who skipped onboarding has no profile yet — not an error.
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

  const patch = useCallback(
    (
      changes: {
        targetBand?: Band;
        dailyMinutes?: number;
        examDate?: string | null;
        consentAi?: boolean;
        consentVoice?: boolean;
      },
      successMessage?: string,
    ): Promise<void> => {
      setIsSaving(true);
      setError(null);
      return profileApi
        .updateProfile(changes)
        .then(updated => {
          setProfile(updated);
          if (successMessage) {
            dispatch(showToast({ message: successMessage, tone: 'success' }));
          }
        })
        .catch(() => setError('Could not save your changes.'))
        .finally(() => setIsSaving(false));
    },
    [dispatch],
  );

  const onChangeTargetBand = useCallback(
    (band: Band): void => {
      patch({ targetBand: band });
    },
    [patch],
  );

  const onChangeDailyMinutes = useCallback(
    (minutes: number): void => {
      patch({ dailyMinutes: minutes });
    },
    [patch],
  );

  const onSaveConsent = useCallback(
    (next: ConsentValues): void => {
      void patch(
        { consentAi: next.consentAi, consentVoice: next.consentVoice },
        'Consent preferences saved.',
      ).then(() => setConsentSheetOpen(false));
    },
    [patch],
  );

  const onChangeExamDate = useCallback(
    (isoDate: string | null): void => {
      void patch(
        { examDate: isoDate },
        isoDate ? 'Exam date updated.' : 'Exam date cleared.',
      ).then(() => {
        setDateSheetOpen(false);
        // The plan was built against the old horizon, so it is rebuilt rather
        // than left quietly stale. Only if one already exists - this must not
        // create a plan for someone who never asked for one.
        void plannerApi
          .getPlan()
          .then(existing => (existing ? plannerApi.generate() : null))
          .catch(() => {
            // Non-fatal: the date change itself already succeeded.
          });
      });
    },
    [patch],
  );

  const onExportData = useCallback((): void => {
    setIsExporting(true);
    meApi
      .exportData()
      .then(data =>
        // Share is part of React Native itself, so the export needs no
        // filesystem permission or native module: the learner picks where it
        // goes (mail, Drive, notes) and the app never touches storage.
        Share.share({
          title: 'My IELTS Master data export',
          message: JSON.stringify(data, null, 2),
        }),
      )
      .catch(() =>
        dispatch(
          showToast({ message: 'Could not export your data.', tone: 'error' }),
        ),
      )
      .finally(() => setIsExporting(false));
  }, [dispatch]);

  const onDeleteAccount = useCallback((): void => {
    setIsDeleting(true);
    meApi
      .deleteAccount()
      .then(() => {
        setDeleteSheetOpen(false);
        // The session is already dead server-side; clear it locally and send
        // the user back to the start rather than into a 401 loop.
        dispatch(logout());
        navigation.reset({ index: 0, routes: [{ name: 'Splash' }] });
      })
      .catch(() =>
        dispatch(
          showToast({
            message: 'Could not delete your account. Please try again.',
            tone: 'error',
          }),
        ),
      )
      .finally(() => setIsDeleting(false));
  }, [dispatch, navigation]);

  const onToggleTheme = useCallback((): void => {
    dispatch(toggleTheme());
  }, [dispatch]);

  const onLogout = useCallback((): void => {
    void dispatch(logoutThunk(refreshToken)).finally(() => {
      navigation.reset({ index: 0, routes: [{ name: 'Splash' }] });
    });
  }, [dispatch, navigation, refreshToken]);

  return {
    user,
    profile,
    isLoading,
    isSaving,
    error,
    themeMode,
    onChangeTargetBand,
    onChangeDailyMinutes,
    consentSheetOpen,
    openConsentSheet: () => setConsentSheetOpen(true),
    closeConsentSheet: () => setConsentSheetOpen(false),
    onSaveConsent,
    dateSheetOpen,
    openDateSheet: () => setDateSheetOpen(true),
    closeDateSheet: () => setDateSheetOpen(false),
    onChangeExamDate,
    isExporting,
    onExportData,
    deleteSheetOpen,
    openDeleteSheet: () => setDeleteSheetOpen(true),
    closeDeleteSheet: () => setDeleteSheetOpen(false),
    isDeleting,
    onDeleteAccount,
    onToggleTheme,
    onLogout,
  };
};
