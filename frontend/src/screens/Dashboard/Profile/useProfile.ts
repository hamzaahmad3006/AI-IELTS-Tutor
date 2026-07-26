/** Profile & settings logic: real profile, editable goals, theme, logout. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { profileApi } from '../../../api';
import {
  logoutThunk,
  toggleTheme,
  useAppDispatch,
  useAppSelector,
} from '../../../redux';
import type {
  AuthenticatedUser,
  Band,
  ProfileResponse,
  RootStackParamList,
} from '../../../types';
import type { ThemeMode } from '../../../constants';

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
  onToggleTheme: () => void;
  onLogout: () => void;
}

export const useProfile = (): UseProfileResult => {
  const dispatch = useAppDispatch();
  const navigation = useNavigation<Nav>();
  const user = useAppSelector((state) => state.auth.user);
  const themeMode = useAppSelector((state) => state.theme.mode);
  const refreshToken = useAppSelector(
    (state) => state.auth.tokens?.refreshToken,
  );

  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    profileApi
      .getProfile()
      .then((data) => {
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
    (changes: { targetBand?: Band; dailyMinutes?: number }): void => {
      setIsSaving(true);
      setError(null);
      profileApi
        .updateProfile(changes)
        .then((updated) => setProfile(updated))
        .catch(() => setError('Could not save your changes.'))
        .finally(() => setIsSaving(false));
    },
    [],
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
    onToggleTheme,
    onLogout,
  };
};
