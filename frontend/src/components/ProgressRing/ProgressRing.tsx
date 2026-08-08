/**
 * A ring that fills toward a daily goal, with the streak in the middle.
 *
 * The arithmetic lives in geometry.ts and is tested there. This file only draws.
 *
 * The flame is drawn rather than animated. An animated flame on a screen the
 * learner opens several times a day is a battery cost and a distraction, and
 * the encouragement comes from the number being there at all rather than from
 * it moving.
 */

import React from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
import { AppText } from '../AppText/AppText';
import { useTheme } from '../theme/useTheme';
import { SPACING } from '@constants';
import {
  circumference,
  dashOffset,
  flameIntensity,
  fractionOf,
  isStreakAlive,
  streakLabel,
} from './geometry';

interface ProgressRingProps {
  /** Minutes studied today. */
  value: number;
  /** The learner's daily goal, in minutes. */
  goal: number;
  streakDays: number;
  size?: number;
  strokeWidth?: number;
}

/** A simple flame outline, drawn in a 24x24 box. */
const FLAME_PATH =
  'M12 2c0 4-4 5-4 9a4 4 0 0 0 8 0c0-2-1-3-1-4 1 1 3 3 3 6a6 6 0 0 1-12 0c0-5 6-7 6-11z';

export const ProgressRing: React.FC<ProgressRingProps> = ({
  value,
  goal,
  streakDays,
  size = 140,
  strokeWidth = 10,
}) => {
  const theme = useTheme();
  const radius = (size - strokeWidth) / 2;
  const fraction = fractionOf(value, goal);
  const alive = isStreakAlive(streakDays);
  const intensity = flameIntensity(streakDays);

  return (
    <View style={styles.wrap} accessibilityRole="image">
      <Svg width={size} height={size}>
        {/* Track. Always drawn, so an empty ring still reads as a ring rather
            than as a missing element. */}
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={theme.colors.containerHigh}
          strokeWidth={strokeWidth}
          fill="none"
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={theme.colors.primary}
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference(radius)}
          strokeDashoffset={dashOffset(radius, fraction)}
          // Rotated so the ring fills from the top rather than from three
          // o'clock, which is where SVG starts and nobody expects.
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </Svg>

      <View style={styles.centre} pointerEvents="none">
        <Svg width={28} height={28} viewBox="0 0 24 24">
          <Path
            d={FLAME_PATH}
            fill={alive ? theme.colors.warning : theme.colors.containerHigh}
            // Opacity carries the streak length. A dead streak is flat grey
            // rather than a faint flame: "almost lit" would suggest a streak
            // that does not exist.
            opacity={alive ? 0.4 + 0.6 * intensity : 1}
          />
        </Svg>
        <AppText variant="labelSm" color="textSecondary">
          {streakLabel(streakDays)}
        </AppText>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', justifyContent: 'center' },
  centre: {
    ...StyleSheet.absoluteFill,
    alignItems: 'center',
    gap: SPACING.xxs,
    justifyContent: 'center',
  },
});
