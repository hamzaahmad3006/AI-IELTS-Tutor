/** Profile & settings logic. */

import { useCallback } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import {
  logoutThunk,
  toggleTheme,
  useAppDispatch,
  useAppSelector,
} from '../../../redux';
import type { AuthenticatedUser, RootStackParamList } from '../../../types';
import type { ThemeMode } from '../../../constants';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UseProfileResult {
  user: AuthenticatedUser | null;
  themeMode: ThemeMode;
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

  const onToggleTheme = useCallback((): void => {
    dispatch(toggleTheme());
  }, [dispatch]);

  const onLogout = useCallback((): void => {
    // Revoke the refresh token server-side, then reset to the entry flow.
    void dispatch(logoutThunk(refreshToken)).finally(() => {
      navigation.reset({ index: 0, routes: [{ name: 'Splash' }] });
    });
  }, [dispatch, navigation, refreshToken]);

  return { user, themeMode, onToggleTheme, onLogout };
};
