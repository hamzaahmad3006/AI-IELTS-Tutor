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
import { getBandColor, SPACING } from '../../../constants';
import type { WritingCriteriaScore, WritingResult } from '../../../types';
import { useWriting } from './useWriting';

const CRITERIA: Array<{ key: keyof WritingCriteriaScore; label: string }> = [
  { key: 'taskResponse', label: 'Task Response' },
  { key: 'coherenceCohesion', label: 'Coherence & Cohesion' },
  { key: 'lexicalResource', label: 'Lexical Resource' },
  { key: 'grammaticalRange', label: 'Grammatical Range' },
];

export const Practice: React.FC = () => {
  const {
    prompt,
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
      <Header title="Writing Task 2" onBack={onBack} />

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
        <AppText variant="labelMd" color={canSubmit ? 'success' : 'textMuted'}>
          {wordCount} words
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
