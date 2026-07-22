/** Elevated surface container (Level 1 card). */

import React from 'react';
import { View, type ViewStyle } from 'react-native';
import { useTheme } from '../theme/useTheme';
import { RADIUS, SPACING, type ShadowToken } from '../../constants';

interface CardProps {
  children: React.ReactNode;
  padding?: number;
  radius?: number;
  shadow?: ShadowToken;
  backgroundToken?: 'card' | 'cardAlt' | 'container';
  style?: ViewStyle;
}

export const Card: React.FC<CardProps> = ({
  children,
  padding = SPACING.lg,
  radius = RADIUS.card,
  shadow = 'card',
  backgroundToken = 'card',
  style,
}) => {
  const theme = useTheme();
  return (
    <View
      style={[
        {
          backgroundColor: theme.colors[backgroundToken],
          borderRadius: radius,
          padding,
        },
        theme.shadows[shadow],
        style,
      ]}
    >
      {children}
    </View>
  );
};
