/** Grammar lessons screen (UI only). Logic in useGrammarLessons. */

import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  Button,
  Card,
  Icon,
  ScreenContainer,
  useTheme,
} from '@components';
import { PALETTE, RADIUS, SPACING } from '@constants';
import type { GrammarExample, GrammarLessonSummary } from '@models';
import { useGrammarLessons } from './useGrammarLessons';

export const Lessons: React.FC = () => {
  const theme = useTheme();
  const {
    lessons,
    recommendedCount,
    selected,
    isLoading,
    isLoadingLesson,
    error,
    openLesson,
    closeLesson,
    onBack,
  } = useGrammarLessons();

  if (isLoading) {
    return (
      <ScreenContainer>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      </ScreenContainer>
    );
  }

  // ---- Lesson detail ----
  if (selected) {
    return (
      <ScreenContainer scroll>
        <View style={styles.header}>
          <Pressable onPress={closeLesson} hitSlop={8}>
            <Icon name="back" size={24} color="primary" />
          </Pressable>
          <AppText variant="titleLg" color="primary">
            Lesson
          </AppText>
          <View style={styles.headerSpacer} />
        </View>

        <AppText variant="headlineMobile">{selected.title}</AppText>
        <AppText variant="labelSm" color="textMuted" style={styles.meta}>
          {selected.level} · {selected.minutes} min
        </AppText>

        <Card style={styles.section}>
          <AppText variant="bodyLg">{selected.body}</AppText>
        </Card>

        {selected.examples.length > 0 ? (
          <>
            <AppText variant="titleLg" style={styles.sectionTitle}>
              Examples
            </AppText>
            {selected.examples.map((example, index) => (
              <ExampleCard key={index} example={example} />
            ))}
          </>
        ) : null}

        <Button
          title="Back to lessons"
          variant="secondary"
          onPress={closeLesson}
          style={styles.section}
        />
      </ScreenContainer>
    );
  }

  // ---- Library ----
  return (
    <ScreenContainer scroll>
      <View style={styles.header}>
        <Pressable onPress={onBack} hitSlop={8}>
          <Icon name="back" size={24} color="primary" />
        </Pressable>
        <AppText variant="titleLg" color="primary">
          Grammar
        </AppText>
        <View style={styles.headerSpacer} />
      </View>

      {error ? (
        <AppText variant="labelMd" color="error" style={styles.error}>
          {error}
        </AppText>
      ) : null}

      {recommendedCount > 0 ? (
        <View
          style={[styles.banner, { backgroundColor: PALETTE.tealContainer }]}
        >
          <Icon name="sparkle" size={18} color="accent" />
          <AppText variant="bodyMd" style={styles.bannerText}>
            {recommendedCount} lesson{recommendedCount === 1 ? '' : 's'} target
            mistakes the AI examiner found in your work.
          </AppText>
        </View>
      ) : null}

      {isLoadingLesson ? (
        <ActivityIndicator
          color={theme.colors.primary}
          style={styles.inlineLoader}
        />
      ) : null}

      {lessons.map(lesson => (
        <LessonCard
          key={lesson.id}
          lesson={lesson}
          onPress={() => openLesson(lesson.id)}
        />
      ))}
    </ScreenContainer>
  );
};

const LessonCard: React.FC<{
  lesson: GrammarLessonSummary;
  onPress: () => void;
}> = ({ lesson, onPress }) => {
  const theme = useTheme();
  return (
    <Pressable onPress={onPress}>
      <Card
        style={StyleSheet.flatten([
          styles.lessonCard,
          lesson.recommended
            ? { borderColor: theme.colors.accent, borderWidth: 2 }
            : null,
        ])}
      >
        <View style={styles.lessonHead}>
          <View style={styles.lessonTitleWrap}>
            <AppText variant="titleLg">{lesson.title}</AppText>
            <AppText variant="labelSm" color="textMuted" style={styles.meta}>
              {lesson.level} · {lesson.minutes} min
            </AppText>
          </View>
          {lesson.recommended ? (
            <View
              style={[styles.pill, { backgroundColor: theme.colors.accent }]}
            >
              <AppText variant="labelSm" color="textInverse">
                FOR YOU
              </AppText>
            </View>
          ) : null}
        </View>
        <AppText variant="bodySm" color="textSecondary" style={styles.summary}>
          {lesson.summary}
        </AppText>
      </Card>
    </Pressable>
  );
};

const ExampleCard: React.FC<{ example: GrammarExample }> = ({ example }) => {
  const theme = useTheme();
  return (
    <Card style={styles.exampleCard}>
      {example.incorrect ? (
        <View style={styles.exampleRow}>
          <Icon name="info" size={16} color="error" />
          <AppText
            variant="bodyMd"
            color="textSecondary"
            style={styles.exampleText}
          >
            {example.incorrect}
          </AppText>
        </View>
      ) : null}
      {example.correct ? (
        <View style={styles.exampleRow}>
          <Icon name="check" size={16} color="success" />
          <AppText variant="bodyMd" style={styles.exampleText}>
            {example.correct}
          </AppText>
        </View>
      ) : null}
      {example.note ? (
        <AppText
          variant="labelSm"
          color="textMuted"
          style={[styles.note, { borderLeftColor: theme.colors.border }]}
        >
          {example.note}
        </AppText>
      ) : null}
    </Card>
  );
};

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: SPACING.md,
  },
  headerSpacer: { width: 24 },
  error: { marginBottom: SPACING.sm },
  meta: { marginTop: 2 },
  section: { marginTop: SPACING.lg },
  sectionTitle: { marginTop: SPACING.lg, marginBottom: SPACING.xs },
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: RADIUS.card,
    padding: SPACING.md,
    marginBottom: SPACING.md,
  },
  bannerText: { flex: 1, marginLeft: SPACING.sm },
  inlineLoader: { marginBottom: SPACING.sm },
  lessonCard: { marginBottom: SPACING.sm },
  lessonHead: { flexDirection: 'row', alignItems: 'flex-start' },
  lessonTitleWrap: { flex: 1 },
  pill: {
    paddingHorizontal: SPACING.xs,
    paddingVertical: 2,
    borderRadius: RADIUS.pill,
  },
  summary: { marginTop: SPACING.xs },
  exampleCard: { marginBottom: SPACING.sm },
  exampleRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: SPACING.xs,
  },
  exampleText: { flex: 1, marginLeft: SPACING.xs },
  note: { marginTop: SPACING.xs, paddingLeft: SPACING.sm, borderLeftWidth: 2 },
});
