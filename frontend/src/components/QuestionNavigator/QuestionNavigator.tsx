/**
 * Numbered jump-to-question strip.
 *
 * The real value in an exam is seeing at a glance which questions are still
 * blank, so answered and unanswered are distinguished by more than colour —
 * the accessibility label says which it is, for anyone who cannot rely on the
 * fill.
 */

import React from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { Card } from '../Card/Card';
import { useTheme } from '../theme/useTheme';
import { RADIUS, SPACING } from '../../constants';

interface QuestionNavigatorProps {
  /** One entry per question, in order. */
  answered: boolean[];
  currentIndex: number;
  onSelect: (index: number) => void;
  testID?: string;
}

export const QuestionNavigator: React.FC<QuestionNavigatorProps> = ({
  answered,
  currentIndex,
  onSelect,
  testID,
}) => {
  const theme = useTheme();
  const remaining = answered.filter((done) => !done).length;

  return (
    <Card style={styles.card} testID={testID ?? 'question-navigator'}>
      <View style={styles.head}>
        <AppText variant="labelMd" color="textSecondary">
          QUESTIONS
        </AppText>
        <AppText variant="labelSm" color="textMuted" testID="navigator-remaining">
          {remaining === 0
            ? 'All answered'
            : `${remaining} left`}
        </AppText>
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.row}
      >
        {answered.map((done, index) => {
          const isCurrent = index === currentIndex;
          return (
            <Pressable
              key={index}
              onPress={() => onSelect(index)}
              accessibilityRole="button"
              accessibilityState={{ selected: isCurrent }}
              accessibilityLabel={`Question ${index + 1}, ${
                done ? 'answered' : 'not answered'
              }`}
              testID={`nav-q-${index + 1}`}
              style={[
                styles.dot,
                {
                  backgroundColor: done
                    ? theme.colors.primary
                    : 'transparent',
                  borderColor: isCurrent
                    ? theme.colors.accent
                    : done
                      ? theme.colors.primary
                      : theme.colors.outline,
                  borderWidth: isCurrent ? 2 : 1,
                },
              ]}
            >
              <AppText
                variant="labelMd"
                color={done ? 'textInverse' : 'textSecondary'}
              >
                {String(index + 1)}
              </AppText>
            </Pressable>
          );
        })}
      </ScrollView>
    </Card>
  );
};

const styles = StyleSheet.create({
  card: { marginTop: SPACING.sm },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  row: { gap: SPACING.sm, paddingTop: SPACING.sm, paddingRight: SPACING.sm },
  dot: {
    width: 38,
    height: 38,
    borderRadius: RADIUS.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
