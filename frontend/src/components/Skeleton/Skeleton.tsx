/**
 * Pulsing placeholder blocks for loading states.
 *
 * Preferred over a bare spinner on screens whose shape is already known: it
 * shows *what* is coming and stops the layout jumping when data lands.
 */

import React from 'react';
import { Animated, StyleSheet, View, type ViewStyle } from 'react-native';
import { useTheme } from '../theme/useTheme';
import { RADIUS, SPACING } from '@constants';

interface SkeletonProps {
  width?: ViewStyle['width'];
  height?: number;
  radius?: number;
  style?: ViewStyle;
  testID?: string;
}

/** Shared pulse so every block on screen breathes in sync, not at random. */
const usePulse = (): Animated.Value => {
  const value = React.useRef(new Animated.Value(0.4)).current;

  React.useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(value, {
          toValue: 1,
          duration: 700,
          useNativeDriver: true,
        }),
        Animated.timing(value, {
          toValue: 0.4,
          duration: 700,
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [value]);

  return value;
};

export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = 16,
  radius = RADIUS.sm,
  style,
  testID,
}) => {
  const theme = useTheme();
  const opacity = usePulse();

  return (
    <Animated.View
      testID={testID}
      accessibilityRole="progressbar"
      accessibilityLabel="Loading"
      style={[
        {
          width,
          height,
          borderRadius: radius,
          backgroundColor: theme.colors.containerHighest,
          opacity,
        },
        style,
      ]}
    />
  );
};

interface SkeletonCardProps {
  /** Body lines drawn under the title. */
  lines?: number;
  testID?: string;
}

/** Card-shaped preset: a short title bar plus body lines. */
export const SkeletonCard: React.FC<SkeletonCardProps> = ({
  lines = 3,
  testID,
}) => {
  const theme = useTheme();
  return (
    <View
      testID={testID ?? 'skeleton-card'}
      style={[styles.card, { backgroundColor: theme.colors.card }]}
    >
      <Skeleton width="45%" height={20} />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          // Taper the last line so the block reads as text, not a table.
          width={i === lines - 1 ? '60%' : '100%'}
          height={12}
          style={styles.line}
        />
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    borderRadius: RADIUS.lg,
    padding: SPACING.md,
    marginTop: SPACING.sm,
  },
  line: { marginTop: SPACING.sm },
});
