/**
 * A live level meter for the microphone.
 *
 * Answers one question: can the app hear you? A candidate who has tapped
 * "answer" and sees nothing move cannot tell whether they are being recorded or
 * whether the app has hung, and on a timed exam that ambiguity costs them the
 * question.
 *
 * Plain Views rather than SVG. These are rectangles, and a View with a height
 * animates on the native thread while an SVG rect re-renders in JavaScript on
 * every frame — for something updating several times a second that difference
 * is the whole cost.
 *
 * The maths is in levels.ts and tested there.
 */

import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useTheme } from '../theme/useTheme';
import { RADIUS } from '@constants';
import { BAR_COUNT, idleLevels, pushLevel } from './levels';

interface WaveformProps {
  /** Current microphone metering in dBFS, or null when not recording. */
  level: number | null;
  active: boolean;
  height?: number;
  barCount?: number;
}

export const Waveform: React.FC<WaveformProps> = ({
  level,
  active,
  height = 48,
  barCount = BAR_COUNT,
}) => {
  const theme = useTheme();
  const [levels, setLevels] = useState<number[]>(() => idleLevels(barCount));
  const previous = useRef<number | null>(null);

  useEffect(() => {
    if (!active) {
      setLevels(idleLevels(barCount));
      previous.current = null;
      return;
    }
    // Only shift when the reading actually changed. Metering fires on a fixed
    // interval whether or not anything moved, and re-rendering on an identical
    // value scrolls the waveform for no reason.
    if (level === previous.current) {
      return;
    }
    previous.current = level;
    setLevels(current => pushLevel(current, level, barCount));
  }, [level, active, barCount]);

  return (
    <View
      style={[styles.row, { height }]}
      // Decorative: the recording state is already announced by the button's
      // own label, and a screen reader reciting bar heights is noise.
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
    >
      {levels.map((fraction, index) => (
        <View
          key={index}
          style={[
            styles.bar,
            {
              height: Math.max(2, fraction * height),
              backgroundColor: active
                ? theme.colors.primary
                : theme.colors.containerHigh,
            },
          ]}
        />
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 3,
    justifyContent: 'center',
  },
  bar: {
    borderRadius: RADIUS.pill,
    width: 3,
  },
});
