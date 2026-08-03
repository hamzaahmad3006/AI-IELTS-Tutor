/** Login screen logic: validation, submit, navigation. */

import { useCallback, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import {
  clearAuthError,
  loginThunk,
  useAppDispatch,
  useAppSelector,
} from '@redux';
import type { RootStackParamList } from '@models';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface LoginErrors {
  email: string | null;
  password: string | null;
}

interface UseLoginResult {
  email: string;
  password: string;
  errors: LoginErrors;
  authError: string | null;
  isSubmitting: boolean;
  onChangeEmail: (value: string) => void;
  onChangePassword: (value: string) => void;
  onSubmit: () => void;
  goToRegister: () => void;
  goToForgot: () => void;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const useLogin = (): UseLoginResult => {
  const dispatch = useAppDispatch();
  const navigation = useNavigation<Nav>();
  const { isBootstrapping, error } = useAppSelector(state => state.auth);

  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [errors, setErrors] = useState<LoginErrors>({
    email: null,
    password: null,
  });

  const validate = useCallback((): boolean => {
    const next: LoginErrors = {
      email: EMAIL_REGEX.test(email) ? null : 'Enter a valid email address',
      password:
        password.length >= 8 ? null : 'Password must be at least 8 characters',
    };
    setErrors(next);
    return next.email === null && next.password === null;
  }, [email, password]);

  const onChangeEmail = useCallback(
    (value: string): void => {
      setEmail(value);
      if (error) {
        dispatch(clearAuthError());
      }
    },
    [dispatch, error],
  );

  const onChangePassword = useCallback(
    (value: string): void => {
      setPassword(value);
      if (error) {
        dispatch(clearAuthError());
      }
    },
    [dispatch, error],
  );

  const onSubmit = useCallback((): void => {
    if (!validate()) {
      return;
    }
    void dispatch(loginThunk({ email, password }))
      .unwrap()
      .then(() => {
        navigation.reset({ index: 0, routes: [{ name: 'Main' }] });
      })
      .catch(() => {
        // error surfaced via auth slice
      });
  }, [dispatch, email, password, validate, navigation]);

  const goToRegister = useCallback((): void => {
    navigation.navigate('Auth', { screen: 'Register' });
  }, [navigation]);

  const goToForgot = useCallback((): void => {
    navigation.navigate('Auth', { screen: 'ForgotPassword' });
  }, [navigation]);

  return {
    email,
    password,
    errors,
    authError: error,
    isSubmitting: isBootstrapping,
    onChangeEmail,
    onChangePassword,
    onSubmit,
    goToRegister,
    goToForgot,
  };
};
