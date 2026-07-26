/** Speaking practice screen (UI only). Logic in useSpeakingPractice. */

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
import type { SpeakingCriteriaScore, SpeakingResult } from '../../../types';
import { useSpeakingPractice } from './useSpeakingPractice';

const CRITERIA: Array<{ key: keyof SpeakingCriteriaScore; label: string }> = [
  { key: 'fluencyCoherence', label: 'Fluency & Coherence' },
  { key: 'lexicalResource', label: 'Lexical Resource' },
  { key: 'grammaticalRange', label: 'Grammatical Range' },
  { key: 'pronunciation', label: 'Pronunciation' },
];

export const Practice: React.FC = () => {
  const theme = useTheme();
  const {
    cueCard,
    phase,
    timerLabel,
    transcript,
    wordCount,
    canSubmit,
    isSubmitting,
    result,
    error,
    setTranscript,
    startSpeaking,
    submit,
    tryAnother,
    onBack,
  } = useSpeakingPractice();

  if (phase === 'scored' && result) {
    return <ResultView result={result} onTryAnother={tryAnother} onBack={onBack} />;
  }

  return (
    <ScreenContainer scroll>
      <Header title="Speaking · Part 2" onBack={onBack} timerLabel={timerLabel} />

      {/* Cue card */}
      <Card style={styles.section} backgroundToken="cardAlt">
        <AppText variant="labelMd" color="textSecondary">
          CUE CARD · {cueCard.topic.toUpperCase()}
        </AppText>
        <AppText variant="titleLg" style={styles.cuePrompt}>
          {cueCard.prompt}
        </AppText>
        <AppText variant="bodySm" color="textSecondary" style={styles.cueLabel}>
          You should say:
        </AppText>
        {cueCard.bulletPoints.map((bullet) => (
          <View key={bullet} style={styles.bulletRow}>
            <View style={[styles.bullet, { backgroundColor: theme.colors.primary }]} />
            <AppText variant="bodyMd" style={styles.bulletText}>
              {bullet}
            </AppText>
          </View>
        ))}
      </Card>

      {phase === 'prep' ? (
        <Card style={styles.section}>
          <AppText variant="titleLg">Preparation time</AppText>
          <AppText variant="bodyMd" color="textSecondary" style={styles.phaseHint}>
            Take up to a minute to plan your answer, then start speaking.
          </AppText>
          <Button
            title="Start speaking"
            icon="mic"
            onPress={startSpeaking}
            style={styles.section}
          />
        </Card>
      ) : (
        <>
          <View style={styles.editorHead}>
            <AppText variant="titleLg">Your response</AppText>
            <AppText variant="labelMd" color={canSubmit ? 'success' : 'textMuted'}>
              {wordCount} words
            </AppText>
          </View>
          <AppText variant="bodySm" color="textMuted" style={styles.dictationHint}>
            Speak your answer aloud and type (or dictate) it here — the AI examiner
            scores the transcript.
          </AppText>
          <Input
            label=""
            value={transcript}
            onChangeText={setTranscript}
            placeholder="Well, the place I'd like to describe is…"
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
        </>
      )}
    </ScreenContainer>
  );
};

const ResultView: React.FC<{
  result: SpeakingResult;
  onTryAnother: () => void;
  onBack: () => void;
}> = ({ result, onTryAnother, onBack }) => {
  const band = result.overallBand ?? 0;
  const bandColor = getBandColor(band);
  return (
    <ScreenContainer scroll>
      <Header title="Speaking Feedback" onBack={onBack} />

      <Card style={styles.section}>
        <View style={styles.resultRow}>
          <View>
            <AppText variant="labelMd" color="textSecondary">
              Estimated Band
            </AppText>
            <AppText variant="displayLg" style={{ color: bandColor }}>
              {band.toFixed(1)}
            </AppText>
            {result.part ? (
              <AppText variant="bodySm" color="textMuted">
                Part {result.part}
              </AppText>
            ) : null}
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
            Examiner feedback
          </AppText>
          <AppText variant="bodyMd" color="textSecondary">
            {result.feedbackSummary}
          </AppText>
        </Card>
      ) : null}

      <Button title="Practice another" onPress={onTryAnother} style={styles.section} />
    </ScreenContainer>
  );
};

const Header: React.FC<{
  title: string;
  onBack: () => void;
  timerLabel?: string;
}> = ({ title, onBack, timerLabel }) => {
  const theme = useTheme();
  return (
    <View style={styles.header}>
      <Pressable onPress={onBack} hitSlop={8}>
        <Icon name="back" size={24} color="primary" />
      </Pressable>
      <AppText variant="titleLg" color="primary">
        {title}
      </AppText>
      {timerLabel ? (
        <View style={[styles.timer, { backgroundColor: theme.colors.primaryContainer }]}>
          <Icon name="timer" size={14} color="primary" />
          <AppText variant="labelMd" color="primary" style={styles.timerText}>
            {timerLabel}
          </AppText>
        </View>
      ) : (
        <View style={styles.headerSpacer} />
      )}
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
  timer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xxs,
    borderRadius: RADIUS.pill,
  },
  timerText: { marginLeft: SPACING.xxs },
  section: { marginTop: SPACING.lg },
  cuePrompt: { marginTop: SPACING.xs },
  cueLabel: { marginTop: SPACING.md, marginBottom: SPACING.xs },
  bulletRow: { flexDirection: 'row', alignItems: 'center', marginBottom: SPACING.xxs },
  bullet: { width: 6, height: 6, borderRadius: 3, marginRight: SPACING.xs },
  bulletText: { flex: 1 },
  phaseHint: { marginTop: SPACING.xs },
  editorHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: SPACING.lg,
    marginBottom: SPACING.xxs,
  },
  dictationHint: { marginBottom: SPACING.xs },
  error: { marginBottom: SPACING.sm },
  resultRow: {
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
