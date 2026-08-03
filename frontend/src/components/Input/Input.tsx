/** Themed text input with label + error state. */

import React, { useState } from 'react';
import { StyleSheet, TextInput, View, type TextInputProps } from 'react-native';
import { AppText } from '../AppText/AppText';
import { useTheme } from '../theme/useTheme';
import { LAYOUT, RADIUS, SPACING } from '@constants';

interface InputProps extends TextInputProps {
  label: string;
  error?: string | null;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  style,
  onFocus,
  onBlur,
  multiline,
  ...rest
}) => {
  const theme = useTheme();
  const [focused, setFocused] = useState<boolean>(false);

  const borderColor = error
    ? theme.colors.error
    : focused
    ? theme.colors.primary
    : theme.colors.border;

  return (
    <View style={styles.wrap}>
      {label ? (
        <AppText variant="labelMd" color="textSecondary" style={styles.label}>
          {label}
        </AppText>
      ) : null}
      <TextInput
        multiline={multiline}
        textAlignVertical={multiline ? 'top' : 'center'}
        placeholderTextColor={theme.colors.textMuted}
        style={[
          styles.input,
          multiline ? styles.multiline : null,
          {
            borderColor,
            color: theme.colors.textPrimary,
            backgroundColor: theme.colors.card,
            borderWidth: focused ? 2 : 1,
          },
          style,
        ]}
        onFocus={e => {
          setFocused(true);
          onFocus?.(e);
        }}
        onBlur={e => {
          setFocused(false);
          onBlur?.(e);
        }}
        {...rest}
      />
      {error ? (
        <AppText variant="labelSm" color="error" style={styles.error}>
          {error}
        </AppText>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: { marginBottom: SPACING.md },
  label: { marginBottom: SPACING.xs },
  input: {
    height: LAYOUT.inputHeight,
    borderRadius: RADIUS.input,
    paddingHorizontal: SPACING.md,
    fontSize: 16,
  },
  multiline: {
    height: undefined,
    minHeight: 180,
    paddingTop: SPACING.sm,
    paddingBottom: SPACING.sm,
  },
  error: { marginTop: SPACING.xxs },
});
