/** Onboarding — exam setup step (UI only). Logic in useExamSetup. */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  Button,
  Card,
  Icon,
  ScreenContainer,
  useTheme,
} from '../../../components';
import { APP_CONFIG, RADIUS, SPACING } from '../../../constants';
import type { ExamType, ProficiencyLevel } from '../../../types';
import { STUDY_TIME_OPTIONS, useExamSetup } from './useExamSetup';

const EXAM_TYPES: Array<{ value: ExamType; label: string; hint: string }> = [
  { value: 'academic', label: 'Academic', hint: 'University admission' },
  { value: 'general', label: 'General Training', hint: 'Migration & work' },
];

const LEVELS: Array<{ value: ProficiencyLevel; label: string }> = [
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
];

export const ExamSetup: React.FC = () => {
  const theme = useTheme();
  const {
    step,
    totalSteps,
    examType,
    selfLevel,
    dailyMinutes,
    consentAi,
    consentVoice,
    targetBand,
    isSubmitting,
    error,
    canSubmit,
    setExamType,
    setSelfLevel,
    setDailyMinutes,
    toggleConsentAi,
    toggleConsentVoice,
    submit,
    onBack,
  } = useExamSetup();

  return (
    <ScreenContainer scroll>
      <View style={styles.header}>
        <Pressable onPress={onBack} hitSlop={8}>
          <Icon name="back" size={24} color="primary" />
        </Pressable>
        <AppText variant="titleLg" color="primary">
          {APP_CONFIG.displayName}
        </AppText>
        <AppText variant="labelMd" color="textSecondary">
          Step {Math.min(step + 1, totalSteps)} of {totalSteps}
        </AppText>
      </View>

      <AppText variant="headlineMobile" style={styles.title}>
        Set up your plan
      </AppText>
      <AppText variant="bodyMd" color="textSecondary" style={styles.subtitle}>
        Targeting Band {targetBand.toFixed(1)} — a few details so your AI tutor can
        personalize your practice.
      </AppText>

      {/* Exam type */}
      <AppText variant="titleLg" style={styles.sectionTitle}>
        Which test?
      </AppText>
      {EXAM_TYPES.map((item) => (
        <SelectRow
          key={item.value}
          label={item.label}
          hint={item.hint}
          selected={examType === item.value}
          onPress={() => setExamType(item.value)}
        />
      ))}

      {/* Level */}
      <AppText variant="titleLg" style={styles.sectionTitle}>
        Your current English level
      </AppText>
      <View style={styles.chipRow}>
        {LEVELS.map((item) => (
          <Chip
            key={item.value}
            label={item.label}
            selected={selfLevel === item.value}
            onPress={() => setSelfLevel(item.value)}
          />
        ))}
      </View>

      {/* Daily study time */}
      <AppText variant="titleLg" style={styles.sectionTitle}>
        Daily study time
      </AppText>
      <View style={styles.chipRow}>
        {STUDY_TIME_OPTIONS.map((minutes) => (
          <Chip
            key={minutes}
            label={`${minutes} min`}
            selected={dailyMinutes === minutes}
            onPress={() => setDailyMinutes(minutes)}
          />
        ))}
      </View>

      {/* Consent */}
      <AppText variant="titleLg" style={styles.sectionTitle}>
        Permissions
      </AppText>
      <ConsentRow
        label="AI processing"
        hint="Required — lets the AI examiner score your answers."
        checked={consentAi}
        onToggle={toggleConsentAi}
      />
      <ConsentRow
        label="Voice recording"
        hint="Optional — needed for spoken interview practice."
        checked={consentVoice}
        onToggle={toggleConsentVoice}
      />

      {error ? (
        <AppText variant="labelMd" color="error" style={styles.error}>
          {error}
        </AppText>
      ) : null}

      <Button
        title="Start learning"
        icon="rocket"
        onPress={submit}
        loading={isSubmitting}
        disabled={!canSubmit}
        style={styles.submit}
      />
      <AppText variant="labelSm" color="textMuted" align="center" style={styles.footnote}>
        Estimated band scores are for practice and are not official IELTS results.
      </AppText>
    </ScreenContainer>
  );
};

const SelectRow: React.FC<{
  label: string;
  hint: string;
  selected: boolean;
  onPress: () => void;
}> = ({ label, hint, selected, onPress }) => {
  const theme = useTheme();
  return (
    <Pressable onPress={onPress}>
      <Card
        style={StyleSheet.flatten([
          styles.selectCard,
          {
            borderColor: selected ? theme.colors.primary : 'transparent',
            borderWidth: selected ? 2 : 0,
          },
        ])}
      >
        <View style={styles.selectRow}>
          <View style={styles.selectText}>
            <AppText variant="titleLg">{label}</AppText>
            <AppText variant="bodySm" color="textSecondary">
              {hint}
            </AppText>
          </View>
          <View
            style={[
              styles.radio,
              { borderColor: selected ? theme.colors.primary : theme.colors.outline },
            ]}
          >
            {selected ? (
              <View style={[styles.radioDot, { backgroundColor: theme.colors.primary }]} />
            ) : null}
          </View>
        </View>
      </Card>
    </Pressable>
  );
};

const Chip: React.FC<{
  label: string;
  selected: boolean;
  onPress: () => void;
}> = ({ label, selected, onPress }) => {
  const theme = useTheme();
  return (
    <Pressable
      onPress={onPress}
      style={[
        styles.chip,
        {
          backgroundColor: selected ? theme.colors.primary : theme.colors.card,
          borderColor: selected ? theme.colors.primary : theme.colors.border,
        },
      ]}
    >
      <AppText variant="labelMd" color={selected ? 'textInverse' : 'textPrimary'}>
        {label}
      </AppText>
    </Pressable>
  );
};

const ConsentRow: React.FC<{
  label: string;
  hint: string;
  checked: boolean;
  onToggle: () => void;
}> = ({ label, hint, checked, onToggle }) => {
  const theme = useTheme();
  return (
    <Pressable onPress={onToggle}>
      <Card style={styles.consentCard}>
        <View style={styles.selectRow}>
          <View style={styles.selectText}>
            <AppText variant="bodyMd">{label}</AppText>
            <AppText variant="labelSm" color="textMuted">
              {hint}
            </AppText>
          </View>
          <View
            style={[
              styles.checkbox,
              {
                backgroundColor: checked ? theme.colors.accent : 'transparent',
                borderColor: checked ? theme.colors.accent : theme.colors.outlineVariant,
              },
            ]}
          >
            {checked ? <Icon name="check" size={14} color="onAccent" /> : null}
          </View>
        </View>
      </Card>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: SPACING.md,
  },
  title: { marginTop: SPACING.xs },
  subtitle: { marginTop: SPACING.xxs },
  sectionTitle: { marginTop: SPACING.lg, marginBottom: SPACING.xs },
  selectCard: { marginBottom: SPACING.sm },
  selectRow: { flexDirection: 'row', alignItems: 'center' },
  selectText: { flex: 1 },
  radio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioDot: { width: 11, height: 11, borderRadius: 6 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap' },
  chip: {
    borderWidth: 1,
    borderRadius: RADIUS.pill,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.xs,
    marginRight: SPACING.xs,
    marginBottom: SPACING.xs,
  },
  consentCard: { marginBottom: SPACING.sm },
  checkbox: {
    width: 26,
    height: 26,
    borderRadius: RADIUS.sm,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  error: { marginTop: SPACING.md },
  submit: { marginTop: SPACING.lg },
  footnote: { marginTop: SPACING.sm },
});
