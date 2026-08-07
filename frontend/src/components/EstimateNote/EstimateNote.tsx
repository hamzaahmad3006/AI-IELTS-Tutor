/**
 * "This is an estimate, not an IELTS score."
 *
 * Every band this app produces comes from a language model reading one piece of
 * work, not from a trained examiner conducting a moderated exam. Shown bare, a
 * number like "6.5" is indistinguishable from the real thing, and a learner who
 * books a test on the strength of it is out the fee.
 *
 * The disclaimer exists at onboarding, but that is once, months before the
 * number that matters appears. This is the version that sits next to the score
 * itself, where the decision is actually being made.
 *
 * Deliberately quiet rather than alarming. Something that shouts undermines the
 * feedback the learner came for; something absent misleads them. A calm line
 * under the number is the honest middle.
 */

import React from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { SPACING } from '@constants';
import { t } from '../../i18n';

interface EstimateNoteProps {
  /** 'full' for result screens, 'short' where space is tight. */
  variant?: 'full' | 'short';
}

export const ESTIMATE_TEXT_FULL = t('score.estimateFull');
export const ESTIMATE_TEXT_SHORT = t('score.estimateShort');

export const EstimateNote: React.FC<EstimateNoteProps> = ({
  variant = 'full',
}) => (
  <View style={styles.wrap}>
    <AppText
      variant="bodySm"
      color="textSecondary"
      align="center"
      // Read out with the score rather than skipped: a screen-reader user must
      // not be the only person who does not learn this is an estimate.
      accessibilityRole="text"
    >
      {variant === 'full' ? ESTIMATE_TEXT_FULL : ESTIMATE_TEXT_SHORT}
    </AppText>
  </View>
);

const styles = StyleSheet.create({
  wrap: {
    marginTop: SPACING.sm,
    paddingHorizontal: SPACING.md,
  },
});
