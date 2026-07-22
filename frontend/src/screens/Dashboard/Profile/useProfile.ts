/** Profile & settings logic. */

import { useCallback } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import {
  logout,
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

  const onToggleTheme = useCallback((): void => {
    dispatch(toggleTheme());
  }, [dispatch]);

  const onLogout = useCallback((): void => {
    dispatch(logout());
    navigation.reset({ index: 0, routes: [{ name: 'Splash' }] });
  }, [dispatch, navigation]);

  return { user, themeMode, onToggleTheme, onLogout };
};
