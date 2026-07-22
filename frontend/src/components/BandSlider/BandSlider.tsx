/**
 * Touch-driven IELTS band slider (0–9, 0.5 steps). Pure JS (no native slider
 * dependency) — uses the responder system with locationX mapping.
 */

import React, { useCallback, useRef, useState } from 'react';
import {
  StyleSheet,
  View,
  type GestureResponderEvent,
  type LayoutChangeEvent,
} from 'react-native';
import { useTheme } from '../theme/useTheme';
import { getBandColor, RADIUS } from '../../constants';

interface BandSliderProps {
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onChange: (band: number) => void;
}

const THUMB = 28;

export const BandSlider: React.FC<BandSliderProps> = ({
  value,
  min = 0,
  max = 9,
  step = 0.5,
  onChange,
}) => {
  const theme = useTheme();
  const widthRef = useRef<number>(0);
  const [trackWidth, setTrackWidth] = useState<number>(0);

  const onLayout = useCallback((e: LayoutChangeEvent): void => {
    widthRef.current = e.nativeEvent.layout.width;
    setTrackWidth(e.nativeEvent.layout.width);
  }, []);

  const applyFromX = useCallback(
    (x: number): void => {
      const width = widthRef.current;
      if (width <= 0) {
        return;
      }
      const ratio = Math.max(0, Math.min(1, x / width));
      const raw = min + ratio * (max - min);
      const stepped = Math.round(raw / step) * step;
      const clamped = Math.max(min, Math.min(max, stepped));
      onChange(Number(clamped.toFixed(1)));
    },
    [min, max, step, onChange],
  );

  const handleTouch = useCallback(
    (e: GestureResponderEvent): void => {
      applyFromX(e.nativeEvent.locationX);
    },
    [applyFromX],
  );

  const ratio = (value - min) / (max - min);
  const fillWidth = Math.max(0, Math.min(1, ratio)) * trackWidth;
  const thumbLeft = Math.max(0, Math.min(trackWidth - THUMB, fillWidth - THUMB / 2));
  const color = getBandColor(value);

  return (
    <View
      style={styles.hitArea}
      onLayout={onLayout}
      onStartShouldSetResponder={() => true}
      onMoveShouldSetResponder={() => true}
      onResponderGrant={handleTouch}
      onResponderMove={handleTouch}
    >
      <View style={[styles.track, { backgroundColor: theme.colors.containerHighest }]}>
        <View
          style={[styles.fill, { width: fillWidth, backgroundColor: color }]}
        />
      </View>
      <View
        style={[
          styles.thumb,
          {
            left: thumbLeft,
            backgroundColor: color,
            borderColor: theme.colors.card,
          },
        ]}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  hitArea: { height: THUMB, justifyContent: 'center' },
  track: { height: 6, borderRadius: RADIUS.pill },
  fill: { height: 6, borderRadius: RADIUS.pill },
  thumb: {
    position: 'absolute',
    width: THUMB,
    height: THUMB,
    borderRadius: THUMB / 2,
    borderWidth: 4,
    top: 0,
  },
});
