/** Themed text primitive. All text in the app should use this component. */

import React from 'react';
import { StyleSheet, Text, type TextProps, type TextStyle } from 'react-native';
import { useTheme } from '../theme/useTheme';
import type { TypographyVariant, ThemeColors } from '../../constants';

type ColorToken = keyof ThemeColors;

interface AppTextProps extends TextProps {
  variant?: TypographyVariant;
  color?: ColorToken;
  align?: TextStyle['textAlign'];
  children: React.ReactNode;
}

export const AppText: React.FC<AppTextProps> = ({
  variant = 'bodyMd',
  color = 'textPrimary',
  align,
  style,
  children,
  ...rest
}) => {
  const theme = useTheme();
  const composed: TextStyle = {
    ...theme.typography[variant],
    color: theme.colors[color],
    ...(align ? { textAlign: align } : null),
  };
  return (
    <Text style={StyleSheet.flatten([composed, style])} {...rest}>
      {children}
    </Text>
  );
};
