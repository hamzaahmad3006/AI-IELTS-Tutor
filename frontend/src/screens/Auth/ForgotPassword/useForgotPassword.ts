/** Forgot-password screen logic (stubbed until backend endpoint exists). */

import { useCallback, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '@models';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UseForgotPasswordResult {
  email: string;
  emailError: string | null;
  isSubmitting: boolean;
  isSent: boolean;
  onChangeEmail: (value: string) => void;
  onSubmit: () => void;
  onBack: () => void;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const useForgotPassword = (): UseForgotPasswordResult => {
  const navigation = useNavigation<Nav>();
  const [email, setEmail] = useState<string>('');
  const [emailError, setEmailError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSent, setIsSent] = useState<boolean>(false);

  const onChangeEmail = useCallback((value: string): void => {
    setEmail(value);
    setEmailError(null);
  }, []);

  const onSubmit = useCallback((): void => {
    if (!EMAIL_REGEX.test(email)) {
      setEmailError('Enter a valid email address');
      return;
    }
    setIsSubmitting(true);
    // TODO: call POST /auth/forgot-password when the backend is ready.
    setTimeout(() => {
      setIsSubmitting(false);
      setIsSent(true);
    }, 700);
  }, [email]);

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    email,
    emailError,
    isSubmitting,
    isSent,
    onChangeEmail,
    onSubmit,
    onBack,
  };
};
