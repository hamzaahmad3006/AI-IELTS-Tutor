/** Splash screen logic: bootstraps session and routes onward. */

import { useEffect } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useAppSelector } from '@redux';
import { APP_CONFIG } from '@constants';
import type { RootStackParamList } from '@models';

type Nav = NativeStackNavigationProp<RootStackParamList, 'Splash'>;

interface UseSplashResult {
  brandMark: string;
  displayName: string;
  tagline: string;
  poweredBy: string;
}

export const useSplash = (): UseSplashResult => {
  const navigation = useNavigation<Nav>();
  const isAuthenticated = useAppSelector(state => state.auth.isAuthenticated);

  useEffect(() => {
    const timer = setTimeout(() => {
      // Unauthenticated users must sign in first: every API call needs a token.
      navigation.reset({
        index: 0,
        routes: [isAuthenticated ? { name: 'Main' } : { name: 'Auth' }],
      });
    }, APP_CONFIG.splashDurationMs);

    return () => clearTimeout(timer);
  }, [navigation, isAuthenticated]);

  return {
    brandMark: APP_CONFIG.brandMark,
    displayName: APP_CONFIG.displayName,
    tagline: APP_CONFIG.tagline,
    poweredBy: APP_CONFIG.poweredBy,
  };
};
