/** Pill-shaped IELTS band indicator, colored by the band scale. */

import React from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { getBandColor, getBandScaleLabel, RADIUS, SPACING } from '@constants';

interface BandBadgeProps {
  band: number;
  /** 'scale' -> RED/AMBER/LIME/GREEN, 'value' -> "Band 7.0". */
  display?: 'scale' | 'value';
}

export const BandBadge: React.FC<BandBadgeProps> = ({
  band,
  display = 'scale',
}) => {
  const color = getBandColor(band);
  const label =
    display === 'scale' ? getBandScaleLabel(band) : `Band ${band.toFixed(1)}`;
  return (
    <View style={[styles.badge, { backgroundColor: color }]}>
      <AppText variant="labelMd" color="textInverse">
        {label}
      </AppText>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    borderRadius: RADIUS.pill,
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xxs,
    alignSelf: 'flex-start',
  },
});
