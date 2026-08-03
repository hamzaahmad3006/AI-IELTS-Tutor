/** Login screen (UI only). Logic in useLogin. */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  Button,
  Icon,
  Input,
  Logo,
  ScreenContainer,
} from '@components';
import { APP_CONFIG, SPACING } from '@constants';
import { useLogin } from './useLogin';

export const Login: React.FC = () => {
  const {
    email,
    password,
    errors,
    authError,
    isSubmitting,
    onChangeEmail,
    onChangePassword,
    onSubmit,
    goToRegister,
    goToForgot,
  } = useLogin();

  return (
    <ScreenContainer scroll>
      <View style={styles.brand}>
        <Logo size={64} />
        <AppText variant="headlineLg" style={styles.brandName}>
          {APP_CONFIG.displayName}
        </AppText>
        <AppText variant="bodyMd" color="textSecondary">
          Welcome back — let's keep improving.
        </AppText>
      </View>

      <Input
        label="Email"
        value={email}
        onChangeText={onChangeEmail}
        error={errors.email}
        autoCapitalize="none"
        keyboardType="email-address"
        placeholder="you@example.com"
      />
      <Input
        label="Password"
        value={password}
        onChangeText={onChangePassword}
        error={errors.password}
        secureTextEntry
        placeholder="••••••••"
      />

      <Pressable onPress={goToForgot} style={styles.forgot}>
        <AppText variant="labelMd" color="primary">
          Forgot password?
        </AppText>
      </Pressable>

      {authError ? (
        <View style={styles.authError}>
          <Icon name="info" size={16} color="error" />
          <AppText variant="labelSm" color="error" style={styles.authErrorText}>
            {authError}
          </AppText>
        </View>
      ) : null}

      <Button
        title="Log In"
        onPress={onSubmit}
        loading={isSubmitting}
        style={styles.submit}
      />

      <View style={styles.footer}>
        <AppText variant="bodyMd" color="textSecondary">
          New here?{' '}
        </AppText>
        <Pressable onPress={goToRegister}>
          <AppText variant="labelMd" color="primary">
            Create an account
          </AppText>
        </Pressable>
      </View>
    </ScreenContainer>
  );
};

const styles = StyleSheet.create({
  brand: { alignItems: 'center', marginVertical: SPACING.xl },
  brandName: { marginTop: SPACING.sm, marginBottom: SPACING.xxs },
  forgot: { alignSelf: 'flex-end', marginBottom: SPACING.md },
  authError: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.md,
  },
  authErrorText: { marginLeft: SPACING.xxs },
  submit: { marginTop: SPACING.xs },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: SPACING.lg,
  },
});
