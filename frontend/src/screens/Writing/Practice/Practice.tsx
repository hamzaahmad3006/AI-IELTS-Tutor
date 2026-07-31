/** Writing practice screen (UI only). Logic in useWriting. */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  BandBadge,
  Button,
  Card,
  Icon,
  Input,
  ProgressBar,
  ScreenContainer,
  useTheme,
} from '../../../components';
import { getBandColor, RADIUS, SPACING } from '../../../constants';
import type {
  ExamType,
  WritingCriteriaScore,
  WritingResult,
} from '../../../types';
import { useWriting, type TimerState } from './useWriting';

const CRITERIA: Array<{ key: keyof WritingCriteriaScore; label: string }> = [
  { key: 'taskResponse', label: 'Task Response' },
  { key: 'coherenceCohesion', label: 'Coherence & Cohesion' },
  { key: 'lexicalResource', label: 'Lexical Resource' },
  { key: 'grammaticalRange', label: 'Grammatical Range' },
];

const EXAM_LABELS: { value: ExamType; label: string }[] = [
  { value: 'academic', label: 'Academic' },
  { value: 'general', label: 'General' },
];

const TaskSelector: React.FC<{
  examType: ExamType;
  taskNumber: number;
  onExamType: (value: ExamType) => void;
  onTaskNumber: (value: number) => void;
}> = ({ examType, taskNumber, onExamType, onTaskNumber }) => (
  <Card style={styles.section} testID="task-selector">
    <AppText variant="labelMd" color="textSecondary">
      PAPER
    </AppText>
    <View style={styles.chipRow}>
      {EXAM_LABELS.map((option) => (
        <Chip
          key={option.value}
          label={option.label}
          selected={examType === option.value}
          onPress={() => onExamType(option.value)}
          testID={`exam-${option.value}`}
        />
      ))}
    </View>

    <AppText variant="labelMd" color="textSecondary" style={styles.selectorLabel}>
      TASK
    </AppText>
    <View style={styles.chipRow}>
      {[1, 2].map((task) => (
        <Chip
          key={task}
          // Task 1 differs by paper: a report in Academic, a letter in General.
          label={
            task === 1
              ? examType === 'academic'
                ? 'Task 1 · Report'
                : 'Task 1 · Letter'
              : 'Task 2 · Essay'
          }
          selected={taskNumber === task}
          onPress={() => onTaskNumber(task)}
          testID={`task-${task}`}
        />
      ))}
    </View>
  </Card>
);

const Chip: React.FC<{
  label: string;
  selected: boolean;
  onPress: () => void;
  testID: string;
}> = ({ label, selected, onPress, testID }) => {
  const theme = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      testID={testID}
      style={[
        styles.chip,
        {
          backgroundColor: selected ? theme.colors.primary : 'transparent',
          borderColor: selected ? theme.colors.primary : theme.colors.outline,
        },
      ]}
    >
      <AppText
        variant="labelMd"
        color={selected ? 'textInverse' : 'textSecondary'}
      >
        {label}
      </AppText>
    </Pressable>
  );
};

export const formatClock = (totalSeconds: number): string => {
  const safe = Math.max(0, totalSeconds);
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
};

const TimerBar: React.FC<{
  secondsLeft: number;
  state: TimerState;
  isWarning: boolean;
  onStart: () => void;
  onPause: () => void;
  onReset: () => void;
}> = ({ secondsLeft, state, isWarning, onStart, onPause, onReset }) => {
  const theme = useTheme();
  const expired = state === 'expired';
  const color = expired
    ? theme.colors.error
    : isWarning
      ? theme.colors.warning
      : theme.colors.textPrimary;

  return (
    <Card style={styles.section} testID="writing-timer">
      <View style={styles.timerRow}>
        <View>
          <AppText variant="labelMd" color="textSecondary">
            TIME REMAINING
          </AppText>
          <AppText variant="displayLg" style={{ color }} testID="timer-clock">
            {formatClock(secondsLeft)}
          </AppText>
        </View>
        <Button
          title={state === 'running' ? 'Pause' : expired ? 'Restart' : 'Start'}
          variant="secondary"
          fullWidth={false}
          onPress={
            state === 'running' ? onPause : expired ? onReset : onStart
          }
          testID="timer-toggle"
        />
      </View>
      {expired ? (
        // Deliberately not a hard stop: the essay stays, and it can still be
        // submitted. A practice timer must never destroy someone's work.
        <AppText variant="labelSm" color="error">
          Time is up. You can still finish and submit — this is practice.
        </AppText>
      ) : null}
    </Card>
  );
};

export const Practice: React.FC = () => {
  const {
    prompt,
    minWords,
    examType,
    taskNumber,
    setExamType,
    setTaskNumber,
    secondsLeft,
    timerState,
    isWarning,
    startTimer,
    pauseTimer,
    resetTimer,
    essayText,
    wordCount,
    canSubmit,
    isSubmitting,
    result,
    error,
    setEssay,
    submit,
    tryAnother,
    onBack,
  } = useWriting();

  if (result) {
    return <ResultView result={result} onTryAnother={tryAnother} onBack={onBack} />;
  }

  return (
    <ScreenContainer scroll>
      <Header title={`Writing Task ${taskNumber}`} onBack={onBack} />

      <TaskSelector
        examType={examType}
        taskNumber={taskNumber}
        onExamType={setExamType}
        onTaskNumber={setTaskNumber}
      />

      <TimerBar
        secondsLeft={secondsLeft}
        state={timerState}
        isWarning={isWarning}
        onStart={startTimer}
        onPause={pauseTimer}
        onReset={resetTimer}
      />

      <Card backgroundToken="cardAlt" style={styles.section}>
        <AppText variant="labelMd" color="textSecondary">
          PROMPT
        </AppText>
        <AppText variant="bodyLg" style={styles.prompt}>
          {prompt}
        </AppText>
      </Card>

      <View style={styles.editorHead}>
        <AppText variant="titleLg">Your response</AppText>
        <AppText
          variant="labelMd"
          color={wordCount >= minWords ? 'success' : 'textMuted'}
        >
          {`${wordCount} / ${minWords} words`}
        </AppText>
      </View>

      <Input
        label=""
        value={essayText}
        onChangeText={setEssay}
        placeholder="Write your essay here…"
        multiline
        autoCapitalize="sentences"
      />

      {error ? (
        <AppText variant="labelMd" color="error" style={styles.error}>
          {error}
        </AppText>
      ) : null}

      <Button
        title="Submit for AI scoring"
        icon="sparkle"
        onPress={submit}
        loading={isSubmitting}
        disabled={!canSubmit}
      />
    </ScreenContainer>
  );
};

const ResultView: React.FC<{
  result: WritingResult;
  onTryAnother: () => void;
  onBack: () => void;
}> = ({ result, onTryAnother, onBack }) => {
  const band = result.overallBand ?? 0;
  const bandColor = getBandColor(band);
  return (
    <ScreenContainer scroll>
      <Header title="Writing Feedback" onBack={onBack} />

      <Card style={styles.section}>
        <View style={styles.overallRow}>
          <View>
            <AppText variant="labelMd" color="textSecondary">
              Overall Band
            </AppText>
            <AppText variant="displayLg" style={{ color: bandColor }}>
              {band.toFixed(1)}
            </AppText>
            <AppText variant="bodySm" color="textMuted">
              {result.wordCount} words
            </AppText>
          </View>
          <BandBadge band={band} />
        </View>
      </Card>

      {result.criteria ? (
        <Card style={styles.section}>
          <AppText variant="titleLg" style={styles.criteriaTitle}>
            Criteria
          </AppText>
          {CRITERIA.map(({ key, label }) => {
            const value = result.criteria ? result.criteria[key] : 0;
            const color = getBandColor(value);
            return (
              <View key={key} style={styles.criteriaRow}>
                <View style={styles.criteriaLabelRow}>
                  <AppText variant="bodyMd">{label}</AppText>
                  <AppText variant="labelMd" style={{ color }}>
                    {value.toFixed(1)}
                  </AppText>
                </View>
                <ProgressBar progress={value / 9} fillColor={color} height={6} />
              </View>
            );
          })}
        </Card>
      ) : null}

      {result.feedbackSummary ? (
        <Card style={styles.section}>
          <AppText variant="titleLg" style={styles.criteriaTitle}>
            Feedback
          </AppText>
          <AppText variant="bodyMd" color="textSecondary">
            {result.feedbackSummary}
          </AppText>
        </Card>
      ) : null}

      {result.improvedEssay ? (
        <Card style={styles.section} backgroundToken="cardAlt">
          <AppText variant="titleLg" style={styles.criteriaTitle}>
            Improved model
          </AppText>
          <AppText variant="bodyLg" color="textSecondary">
            {result.improvedEssay}
          </AppText>
        </Card>
      ) : null}

      <Button title="Write another" onPress={onTryAnother} style={styles.section} />
    </ScreenContainer>
  );
};

const Header: React.FC<{ title: string; onBack: () => void }> = ({
  title,
  onBack,
}) => {
  const theme = useTheme();
  return (
    <View style={styles.header}>
      <Pressable onPress={onBack} hitSlop={8}>
        <Icon name="back" size={24} color="primary" />
      </Pressable>
      <AppText variant="titleLg" color="primary">
        {title}
      </AppText>
      <View style={styles.headerSpacer} />
    </View>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: SPACING.md,
  },
  headerSpacer: { width: 24 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: SPACING.sm, marginTop: SPACING.sm },
  chip: {
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.md,
    borderRadius: RADIUS.pill,
    borderWidth: 1,
  },
  selectorLabel: { marginTop: SPACING.md },
  timerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  section: { marginTop: SPACING.lg },
  prompt: { marginTop: SPACING.xs },
  editorHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: SPACING.lg,
    marginBottom: SPACING.xs,
  },
  error: { marginBottom: SPACING.sm },
  overallRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  criteriaTitle: { marginBottom: SPACING.md },
  criteriaRow: { marginBottom: SPACING.md },
  criteriaLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.xs,
  },
});
