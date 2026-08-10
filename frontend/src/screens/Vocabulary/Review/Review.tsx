/** Vocabulary review screen (UI only). Logic in useVocabularyReview. */

import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  Button,
  Card,
  Icon,
  ProgressBar,
  ScreenContainer,
  useTheme,
} from '@components';
import { ON_BRIGHT_FILL, PALETTE, RADIUS, SPACING } from '@constants';
import type { VocabGrade } from '@models';
import { useVocabularyReview } from './useVocabularyReview';

/** Recall buttons map to SM-2 grades. */
const GRADES: Array<{ label: string; grade: VocabGrade; color: string }> = [
  { label: 'Forgot', grade: 1, color: PALETTE.error },
  { label: 'Hard', grade: 3, color: PALETTE.warning },
  { label: 'Good', grade: 4, color: PALETTE.teal },
  { label: 'Easy', grade: 5, color: PALETTE.success },
];

export const Review: React.FC = () => {
  const theme = useTheme();
  const {
    card,
    stats,
    position,
    total,
    isRevealed,
    isLoading,
    isFinished,
    reviewedCount,
    error,
    reveal,
    grade,
    restart,
    onBack,
  } = useVocabularyReview();

  if (isLoading) {
    return (
      <ScreenContainer>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer scroll>
      <View style={styles.header}>
        <Pressable onPress={onBack} hitSlop={8}>
          <Icon name="back" size={24} color="primary" />
        </Pressable>
        <AppText variant="titleLg" color="primary">
          Vocabulary
        </AppText>
        <AppText variant="labelMd" color="textSecondary">
          {total > 0 ? `${position}/${total}` : ''}
        </AppText>
      </View>

      {error ? (
        <AppText variant="labelMd" color="error" style={styles.error}>
          {error}
        </AppText>
      ) : null}

      {/* Session complete */}
      {isFinished || !card ? (
        <>
          <Card style={styles.section} backgroundToken="cardAlt">
            <AppText variant="headlineMd">
              {reviewedCount > 0 ? 'Session complete' : 'Nothing due right now'}
            </AppText>
            <AppText variant="bodyMd" color="textSecondary" style={styles.body}>
              {reviewedCount > 0
                ? `You reviewed ${reviewedCount} word${
                    reviewedCount === 1 ? '' : 's'
                  }. Cards you found hard will come back sooner.`
                : 'New words appear here as you practise, and reviews are scheduled automatically.'}
            </AppText>
          </Card>
          {stats ? <StatsCard stats={stats} /> : null}
          <Button
            title="Start another session"
            onPress={restart}
            style={styles.section}
          />
        </>
      ) : (
        <>
          <ProgressBar
            progress={total > 0 ? (position - 1) / total : 0}
            height={6}
            style={styles.progress}
          />

          {/* Flashcard */}
          <Card style={styles.cardFace}>
            {card.isNew ? (
              <View
                style={[
                  styles.pill,
                  { backgroundColor: theme.colors.primaryContainer },
                ]}
              >
                <AppText variant="labelSm" color="primary">
                  NEW WORD
                </AppText>
              </View>
            ) : null}

            <AppText variant="displayLg" align="center" style={styles.word}>
              {card.word}
            </AppText>

            {card.cefrLevel || card.lexicalField ? (
              <AppText variant="labelSm" color="textMuted" align="center">
                {[card.cefrLevel, card.lexicalField]
                  .filter(Boolean)
                  .join(' · ')}
              </AppText>
            ) : null}

            {isRevealed ? (
              <View style={styles.answer}>
                <AppText variant="bodyLg" align="center">
                  {card.definition}
                </AppText>
                {card.example ? (
                  <AppText
                    variant="bodyMd"
                    color="textSecondary"
                    align="center"
                    style={styles.example}
                  >
                    “{card.example}”
                  </AppText>
                ) : null}
              </View>
            ) : (
              <AppText
                variant="bodyMd"
                color="textMuted"
                align="center"
                style={styles.answer}
              >
                Do you remember what this means?
              </AppText>
            )}
          </Card>

          {isRevealed ? (
            <>
              <AppText
                variant="labelMd"
                color="textSecondary"
                style={styles.gradeLabel}
              >
                How well did you recall it?
              </AppText>
              <View style={styles.gradeRow}>
                {GRADES.map(option => (
                  <Pressable
                    key={option.label}
                    onPress={() => grade(option.grade)}
                    style={[
                      styles.gradeButton,
                      { backgroundColor: option.color },
                    ]}
                  >
                    {/* Fixed ink: the grade fills are PALETTE constants that
                        do not follow the theme, so a label that does lands as
                        white on amber in light mode. */}
                    <AppText variant="labelMd" style={styles.gradeButtonLabel}>
                      {option.label}
                    </AppText>
                  </Pressable>
                ))}
              </View>
            </>
          ) : (
            <Button
              title="Show definition"
              onPress={reveal}
              style={styles.section}
            />
          )}
        </>
      )}
    </ScreenContainer>
  );
};

const StatsCard: React.FC<{
  stats: {
    totalItems: number;
    started: number;
    dueNow: number;
    mastered: number;
  };
}> = ({ stats }) => (
  <Card style={styles.section}>
    <AppText variant="titleLg" style={styles.body}>
      Your vocabulary
    </AppText>
    {[
      { label: 'Words in bank', value: stats.totalItems },
      { label: 'Started', value: stats.started },
      { label: 'Due now', value: stats.dueNow },
      { label: 'Mastered', value: stats.mastered },
    ].map(row => (
      <View key={row.label} style={styles.statRow}>
        <AppText variant="bodyMd">{row.label}</AppText>
        <AppText variant="labelMd" color="primary">
          {row.value}
        </AppText>
      </View>
    ))}
  </Card>
);

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: SPACING.md,
  },
  error: { marginBottom: SPACING.sm },
  section: { marginTop: SPACING.lg },
  body: { marginTop: SPACING.xs },
  progress: { marginBottom: SPACING.md },
  cardFace: { paddingVertical: SPACING.xl, alignItems: 'center' },
  pill: {
    paddingHorizontal: SPACING.sm,
    paddingVertical: 2,
    borderRadius: RADIUS.pill,
    marginBottom: SPACING.sm,
  },
  word: { marginBottom: SPACING.xs },
  answer: { marginTop: SPACING.lg },
  example: { marginTop: SPACING.sm, fontStyle: 'italic' },
  gradeLabel: { marginTop: SPACING.lg, marginBottom: SPACING.xs },
  gradeRow: { flexDirection: 'row', flexWrap: 'wrap' },
  gradeButtonLabel: { color: ON_BRIGHT_FILL },
  gradeButton: {
    flexGrow: 1,
    alignItems: 'center',
    paddingVertical: SPACING.sm,
    borderRadius: RADIUS.button,
    marginRight: SPACING.xs,
    marginBottom: SPACING.xs,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: SPACING.xs,
  },
});
