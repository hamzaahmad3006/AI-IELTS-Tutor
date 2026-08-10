/** Study plan screen (UI only). Logic in usePlan. */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  Button,
  Card,
  EmptyState,
  Icon,
  ProgressBar,
  ScreenContainer,
  SkeletonCard,
  useTheme,
} from '@components';
import { RADIUS, SPACING } from '@constants';
import type { PlanTask } from '@models';
import { usePlan } from './usePlan';

export const Plan: React.FC = () => {
  const theme = useTheme();
  const {
    plan,
    isLoading,
    isGenerating,
    error,
    weeks,
    activeWeek,
    setActiveWeek,
    tasksForWeek,
    generate,
    toggleTask,
    onBack,
  } = usePlan();

  if (isLoading) {
    return (
      <ScreenContainer scroll>
        <SkeletonCard lines={2} />
        <SkeletonCard lines={4} />
      </ScreenContainer>
    );
  }

  if (isGenerating && !plan) {
    // The "generating plan" state: honest about what is happening rather than
    // a bare spinner.
    return (
      <ScreenContainer>
        <View style={styles.center} testID="plan-generating">
          <Icon name="sparkle" size={44} color="primary" />
          <AppText variant="titleLg" align="center" style={styles.centerTitle}>
            Building your plan
          </AppText>
          <AppText variant="bodySm" color="textSecondary" align="center">
            Weighting sessions towards the modules furthest from your target.
          </AppText>
        </View>
      </ScreenContainer>
    );
  }

  if (!plan) {
    return (
      <ScreenContainer>
        <EmptyState
          variant="empty"
          title="No study plan yet"
          message={
            error ??
            'Build one from your target band, exam date and the time you can give each day.'
          }
          actionLabel={isGenerating ? 'Building…' : 'Build my plan'}
          onAction={generate}
          testID="plan-empty"
        />
      </ScreenContainer>
    );
  }

  const progress = plan.totalCount ? plan.completedCount / plan.totalCount : 0;

  return (
    <ScreenContainer scroll>
      <View style={styles.header}>
        <Pressable
          onPress={onBack}
          accessibilityRole="button"
          accessibilityLabel="Back"
        >
          <Icon name="back" size={22} color="primary" />
        </Pressable>
        <AppText variant="titleLg" style={styles.grow}>
          Study plan
        </AppText>
      </View>

      <Card style={styles.section} testID="plan-summary">
        <AppText variant="labelMd" color="textSecondary">
          {`${plan.completedCount} of ${plan.totalCount} sessions done`}
        </AppText>
        <ProgressBar
          progress={progress}
          height={6}
          fillColor={theme.colors.primary}
          style={styles.progress}
        />
        <AppText
          variant="bodySm"
          color="textSecondary"
          style={styles.rationale}
        >
          {plan.rationale}
        </AppText>
      </Card>

      <View style={styles.weekRow}>
        {weeks.map(week => {
          const selected = week === activeWeek;
          return (
            <Pressable
              key={week}
              onPress={() => setActiveWeek(week)}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              accessibilityLabel={`Week ${week}`}
              testID={`plan-week-${week}`}
              style={[
                styles.weekChip,
                {
                  backgroundColor: selected
                    ? theme.colors.primary
                    : 'transparent',
                  borderColor: selected
                    ? theme.colors.primary
                    : theme.colors.outline,
                },
              ]}
            >
              <AppText
                variant="labelMd"
                color={selected ? 'textInverse' : 'textSecondary'}
              >
                {`W${week}`}
              </AppText>
            </Pressable>
          );
        })}
      </View>

      {tasksForWeek.map(task => (
        <TaskRow key={task.id} task={task} onToggle={() => toggleTask(task)} />
      ))}

      <Button
        title={isGenerating ? 'Rebuilding…' : 'Rebuild plan'}
        variant="secondary"
        onPress={generate}
        disabled={isGenerating}
        style={styles.section}
        testID="plan-rebuild"
      />
    </ScreenContainer>
  );
};

const TaskRow: React.FC<{ task: PlanTask; onToggle: () => void }> = ({
  task,
  onToggle,
}) => {
  const theme = useTheme();
  return (
    <Pressable
      onPress={onToggle}
      accessibilityRole="checkbox"
      accessibilityState={{ checked: task.isDone }}
      accessibilityLabel={`${task.title}, ${task.minutes} minutes`}
      testID={`plan-task-${task.id}`}
    >
      <Card style={styles.taskCard}>
        <View style={styles.taskRow}>
          <View
            style={[
              styles.check,
              {
                backgroundColor: task.isDone
                  ? theme.colors.accent
                  : 'transparent',
                borderColor: task.isDone
                  ? theme.colors.accent
                  : theme.colors.outline,
              },
            ]}
          >
            {task.isDone ? (
              <Icon name="check" size={14} color="onAccent" />
            ) : null}
          </View>
          <View style={styles.grow}>
            <AppText
              variant="bodyMd"
              style={task.isDone ? styles.doneText : undefined}
            >
              {task.title}
            </AppText>
            <AppText variant="labelSm" color="textMuted">
              {task.detail}
            </AppText>
          </View>
          <AppText variant="labelSm" color="textMuted">
            {`${task.minutes}m`}
          </AppText>
        </View>
      </Card>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    marginBottom: SPACING.md,
  },
  grow: { flex: 1 },
  section: { marginTop: SPACING.md },
  progress: { marginTop: SPACING.sm },
  rationale: { marginTop: SPACING.sm },
  weekRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: SPACING.sm,
    marginTop: SPACING.md,
  },
  weekChip: {
    borderWidth: 1,
    borderRadius: RADIUS.pill,
    paddingVertical: 6,
    paddingHorizontal: SPACING.md,
  },
  taskCard: { marginTop: SPACING.sm },
  taskRow: { flexDirection: 'row', alignItems: 'center', gap: SPACING.sm },
  check: {
    width: 24,
    height: 24,
    borderRadius: RADIUS.sm,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  doneText: { textDecorationLine: 'line-through' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  centerTitle: { marginTop: SPACING.md, marginBottom: SPACING.xs },
});
