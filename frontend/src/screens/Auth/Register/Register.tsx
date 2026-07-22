/** Register screen (UI only). Logic in useRegister. */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  Button,
  Input,
  Logo,
  ScreenContainer,
} from '../../../components';
import { SPACING } from '../../../constants';
import { useRegister } from './useRegister';

export const Register: React.FC = () => {
  const {
    fullName,
    email,
    password,
    errors,
    authError,
    isSubmitting,
    onChangeFullName,
    onChangeEmail,
    onChangePassword,
    onSubmit,
    goToLogin,
  } = useRegister();

  return (
    <ScreenContainer scroll>
      <View style={styles.brand}>
        <Logo size={56} />
        <AppText variant="headlineLg" style={styles.brandName}>
          Create your account
        </AppText>
        <AppText variant="bodyMd" color="textSecondary" align="center">
          Start your personalized IELTS journey today.
        </AppText>
      </View>

      <Input
        label="Full Name"
        value={fullName}
        onChangeText={onChangeFullName}
        error={errors.fullName}
        placeholder="Sarah Ahmed"
      />
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
        placeholder="At least 8 characters"
      />

      {authError ? (
        <AppText variant="labelSm" color="error" style={styles.authError}>
          {authError}
        </AppText>
      ) : null}

      <Button
        title="Create Account"
        onPress={onSubmit}
        loading={isSubmitting}
        style={styles.submit}
      />

      <View style={styles.footer}>
        <AppText variant="bodyMd" color="textSecondary">
          Already have an account?{' '}
        </AppText>
        <Pressable onPress={goToLogin}>
          <AppText variant="labelMd" color="primary">
            Log in
          </AppText>
        </Pressable>
      </View>
    </ScreenContainer>
  );
};

const styles = StyleSheet.create({
  brand: { alignItems: 'center', marginVertical: SPACING.xl },
  brandName: { marginTop: SPACING.sm, marginBottom: SPACING.xxs },
  authError: { marginBottom: SPACING.sm },
  submit: { marginTop: SPACING.xs },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: SPACING.lg,
  },
});
