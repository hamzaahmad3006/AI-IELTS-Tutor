/** Forgot-password screen (UI only). Logic in useForgotPassword. */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  Button,
  Icon,
  Input,
  ScreenContainer,
} from '../../../components';
import { SPACING } from '../../../constants';
import { useForgotPassword } from './useForgotPassword';

export const ForgotPassword: React.FC = () => {
  const {
    email,
    emailError,
    isSubmitting,
    isSent,
    onChangeEmail,
    onSubmit,
    onBack,
  } = useForgotPassword();

  return (
    <ScreenContainer scroll>
      <Pressable onPress={onBack} hitSlop={8} style={styles.back}>
        <Icon name="back" size={24} color="primary" />
      </Pressable>

      <AppText variant="headlineMobile" style={styles.title}>
        Reset password
      </AppText>
      <AppText variant="bodyMd" color="textSecondary" style={styles.subtitle}>
        Enter your email and we'll send you a link to reset your password.
      </AppText>

      {isSent ? (
        <View style={styles.sent}>
          <Icon name="check" size={20} color="success" />
          <AppText variant="bodyMd" color="success" style={styles.sentText}>
            If an account exists for {email}, a reset link is on its way.
          </AppText>
        </View>
      ) : (
        <>
          <Input
            label="Email"
            value={email}
            onChangeText={onChangeEmail}
            error={emailError}
            autoCapitalize="none"
            keyboardType="email-address"
            placeholder="you@example.com"
          />
          <Button
            title="Send reset link"
            onPress={onSubmit}
            loading={isSubmitting}
            style={styles.submit}
          />
        </>
      )}
    </ScreenContainer>
  );
};

const styles = StyleSheet.create({
  back: { marginVertical: SPACING.md },
  title: { marginTop: SPACING.md },
  subtitle: { marginTop: SPACING.xs, marginBottom: SPACING.lg },
  submit: { marginTop: SPACING.xs },
  sent: { flexDirection: 'row', alignItems: 'center', marginTop: SPACING.md },
  sentText: { marginLeft: SPACING.xs, flex: 1 },
});
