/**
 * Difficulty picker for Reading and Listening.
 *
 * `adaptive` is the default and stays a first-class option rather than being
 * replaced by whatever level it resolved to: a learner who overrides to Hard
 * needs an obvious way back to letting the app choose.
 *
 * The level actually served is shown alongside, because the content bank does
 * not guarantee every level exists for every paper and silently substituting
 * one would misrepresent the practice.
 */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { Card } from '../Card/Card';
import { useTheme } from '../theme/useTheme';
import { RADIUS, SPACING } from '../../constants';
import type { Difficulty } from '../../types';

const OPTIONS: { value: Difficulty; label: string }[] = [
  { value: 'adaptive', label: 'Adaptive' },
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
];

interface DifficultySelectorProps {
  value: Difficulty;
  onChange: (value: Difficulty) => void;
  /** Level of the content actually returned, when known. */
  served?: string | null;
  disabled?: boolean;
  testID?: string;
}

export const DifficultySelector: React.FC<DifficultySelectorProps> = ({
  value,
  onChange,
  served,
  disabled = false,
  testID,
}) => {
  const theme = useTheme();

  return (
    <Card style={styles.card} testID={testID ?? 'difficulty-selector'}>
      <View style={styles.headRow}>
        <AppText variant="labelMd" color="textSecondary">
          DIFFICULTY
        </AppText>
        {served ? (
          <AppText variant="labelSm" color="textMuted" testID="difficulty-served">
            {value === 'adaptive' ? `Chose ${served}` : `Serving ${served}`}
          </AppText>
        ) : null}
      </View>

      <View style={styles.row}>
        {OPTIONS.map((option) => {
          const selected = value === option.value;
          return (
            <Pressable
              key={option.value}
              disabled={disabled}
              onPress={() => onChange(option.value)}
              accessibilityRole="button"
              accessibilityState={{ selected, disabled }}
              accessibilityLabel={option.label}
              testID={`difficulty-${option.value}`}
              style={[
                styles.chip,
                {
                  backgroundColor: selected
                    ? theme.colors.primary
                    : 'transparent',
                  borderColor: selected
                    ? theme.colors.primary
                    : theme.colors.outline,
                  opacity: disabled ? 0.5 : 1,
                },
              ]}
            >
              <AppText
                variant="labelMd"
                color={selected ? 'textInverse' : 'textSecondary'}
              >
                {option.label}
              </AppText>
            </Pressable>
          );
        })}
      </View>
    </Card>
  );
};

const styles = StyleSheet.create({
  card: { marginTop: SPACING.sm },
  headRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: SPACING.sm,
    marginTop: SPACING.sm,
  },
  chip: {
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.md,
    borderRadius: RADIUS.pill,
    borderWidth: 1,
  },
});
