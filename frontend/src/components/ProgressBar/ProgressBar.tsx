/** Rounded track/fill progress bar. */

import React from 'react';
import { View, type ViewStyle } from 'react-native';
import { useTheme } from '../theme/useTheme';
import { RADIUS, type ThemeColors } from '@constants';

interface ProgressBarProps {
  /** 0..1 */
  progress: number;
  height?: number;
  trackColor?: keyof ThemeColors;
  fillColor?: string;
  style?: ViewStyle;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  height = 8,
  trackColor = 'containerHighest',
  fillColor,
  style,
}) => {
  const theme = useTheme();
  const clamped = Math.max(0, Math.min(1, progress));
  return (
    <View
      style={[
        {
          height,
          borderRadius: RADIUS.pill,
          backgroundColor: theme.colors[trackColor],
          overflow: 'hidden',
        },
        style,
      ]}
    >
      <View
        style={{
          height: '100%',
          width: `${clamped * 100}%`,
          borderRadius: RADIUS.pill,
          backgroundColor: fillColor ?? theme.colors.accent,
        }}
      />
    </View>
  );
};
