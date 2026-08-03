/** Register screen logic: validation, submit, navigation. */

import { useCallback, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import {
  clearAuthError,
  registerThunk,
  useAppDispatch,
  useAppSelector,
} from '@redux';
import type { RootStackParamList } from '@models';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface RegisterErrors {
  fullName: string | null;
  email: string | null;
  password: string | null;
}

interface UseRegisterResult {
  fullName: string;
  email: string;
  password: string;
  errors: RegisterErrors;
  authError: string | null;
  isSubmitting: boolean;
  onChangeFullName: (value: string) => void;
  onChangeEmail: (value: string) => void;
  onChangePassword: (value: string) => void;
  onSubmit: () => void;
  goToLogin: () => void;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const useRegister = (): UseRegisterResult => {
  const dispatch = useAppDispatch();
  const navigation = useNavigation<Nav>();
  const { isBootstrapping, error } = useAppSelector(state => state.auth);

  const [fullName, setFullName] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [errors, setErrors] = useState<RegisterErrors>({
    fullName: null,
    email: null,
    password: null,
  });

  const validate = useCallback((): boolean => {
    const next: RegisterErrors = {
      fullName: fullName.trim().length >= 2 ? null : 'Enter your full name',
      email: EMAIL_REGEX.test(email) ? null : 'Enter a valid email address',
      password:
        password.length >= 8 ? null : 'Password must be at least 8 characters',
    };
    setErrors(next);
    return !next.fullName && !next.email && !next.password;
  }, [fullName, email, password]);

  const clearIfError = useCallback((): void => {
    if (error) {
      dispatch(clearAuthError());
    }
  }, [dispatch, error]);

  const onChangeFullName = useCallback(
    (value: string): void => {
      setFullName(value);
      clearIfError();
    },
    [clearIfError],
  );

  const onChangeEmail = useCallback(
    (value: string): void => {
      setEmail(value);
      clearIfError();
    },
    [clearIfError],
  );

  const onChangePassword = useCallback(
    (value: string): void => {
      setPassword(value);
      clearIfError();
    },
    [clearIfError],
  );

  const onSubmit = useCallback((): void => {
    if (!validate()) {
      return;
    }
    void dispatch(registerThunk({ fullName, email, password }))
      .unwrap()
      .then(() => {
        navigation.reset({ index: 0, routes: [{ name: 'Onboarding' }] });
      })
      .catch(() => {
        // error surfaced via auth slice
      });
  }, [dispatch, fullName, email, password, validate, navigation]);

  const goToLogin = useCallback((): void => {
    navigation.navigate('Auth', { screen: 'Login' });
  }, [navigation]);

  return {
    fullName,
    email,
    password,
    errors,
    authError: error,
    isSubmitting: isBootstrapping,
    onChangeFullName,
    onChangeEmail,
    onChangePassword,
    onSubmit,
    goToLogin,
  };
};
