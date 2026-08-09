/**
 * The spoken IELTS Speaking test.
 *
 * Renders whatever phase the server's examiner state machine is in. Each phase
 * genuinely needs different controls — a cue card with a silent countdown is
 * not a question with a record button — so they are branched explicitly rather
 * than squeezed into one layout with things conditionally hidden.
 *
 * Nothing here decides exam rules. Durations, question text and phase order all
 * arrive from the server; this file only draws them.
 */

import React, { useCallback, useEffect } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  BandBadge,
  Button,
  EstimateNote,
  Card,
  Icon,
  ProgressBar,
  ScreenContainer,
  Waveform,
  useTheme,
} from '@components';
import { RADIUS, SPACING } from '@constants';
import type { InterviewPhase } from '@models';
import { t } from '../../../i18n';
import { useExaminerSession } from './useExaminerSession';
import { useSpokenAnswer } from './useSpokenAnswer';

const phaseLabel = (phase: InterviewPhase): string =>
  t(`interview.phase.${phase}` as Parameters<typeof t>[0]);

const formatClock = (seconds: number): string => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
};

export const ExaminerInterview: React.FC = () => {
  const theme = useTheme();
  const exam = useExaminerSession();
  const answerWithAudio = exam.answerWithAudio;

  const onAnswer = useCallback(
    async (file: { uri: string; name: string; type: string }) => {
      await answerWithAudio(file);
    },
    [answerWithAudio],
  );

  const mic = useSpokenAnswer({ onAnswer });

  useEffect(() => {
    void exam.start();
    // Intentionally once: re-running would abandon the exam in progress and
    // start a second one, losing every answer given so far.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { session, secondsLeft, result } = exam;
  const phase = session?.phase;
  const action = session?.action;

  // The exam is finished; ask for the band.
  useEffect(() => {
    if (session?.phase === 'scoring' && !result && !exam.isSubmitting) {
      void exam.score();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.phase, result]);

  if (exam.isLoading || !session || !action) {
    return (
      <ScreenContainer>
        <View style={styles.centred}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
          <AppText variant="bodyMd" color="textSecondary" style={styles.gap}>
            {exam.error ?? t('interview.preparing')}
          </AppText>
          {exam.error ? (
            <Button
              title={t('interview.retry')}
              onPress={() => void exam.start()}
            />
          ) : null}
        </View>
      </ScreenContainer>
    );
  }

  if (result) {
    return (
      <ScreenContainer>
        <View style={styles.centred}>
          <AppText variant="titleLg" color="primary">
            {t('interview.complete')}
          </AppText>
          <BandBadge band={result.overallBand ?? 0} display="value" />
          <EstimateNote />
          <AppText
            variant="bodyMd"
            color="textSecondary"
            align="center"
            style={styles.gap}
          >
            {result.feedbackSummary ?? ''}
          </AppText>
        </View>
      </ScreenContainer>
    );
  }

  const isTimed = secondsLeft !== null;
  const busy = exam.isSubmitting || mic.isUploading;

  return (
    <ScreenContainer>
      <View style={styles.header}>
        <AppText variant="labelMd" color="textSecondary">
          {phaseLabel(session.phase)}
        </AppText>
        {isTimed ? (
          <View
            style={[
              styles.timer,
              { backgroundColor: theme.colors.primaryContainer },
            ]}
          >
            <Icon name="timer" size={16} color="primary" />
            <AppText variant="labelMd" style={styles.timerText}>
              {formatClock(secondsLeft ?? 0)}
            </AppText>
          </View>
        ) : null}
      </View>

      <ProgressBar
        progress={
          session.progress.phaseIndex / Math.max(1, session.progress.phaseCount)
        }
      />

      <Card style={styles.prompt}>
        <AppText variant="bodyLg" color="textPrimary">
          {action.text}
        </AppText>

        {action.bullets.length > 0 ? (
          <View style={styles.bullets}>
            <AppText variant="labelMd" color="textSecondary">
              {t('interview.youShouldSay')}
            </AppText>
            {action.bullets.map(bullet => (
              <AppText
                key={bullet}
                variant="bodyMd"
                color="textSecondary"
                style={styles.bullet}
              >
                {'•'} {bullet}
              </AppText>
            ))}
          </View>
        ) : null}
      </Card>

      {mic.error ? (
        <AppText variant="bodySm" color="error" style={styles.error}>
          {mic.error}
        </AppText>
      ) : null}
      {exam.error ? (
        <AppText variant="bodySm" color="error" style={styles.error}>
          {exam.error}
        </AppText>
      ) : null}

      <View style={styles.controls}>
        {phase === 'part2_cue' ? (
          <Button
            title={t('interview.ready')}
            onPress={() => void exam.answer('', 'typed')}
            disabled={busy}
          />
        ) : null}

        {phase === 'part2_prep' ? (
          <>
            <AppText
              variant="bodySm"
              color="textSecondary"
              align="center"
              style={styles.hint}
            >
              {t('interview.prepHint')}
            </AppText>
            <Button
              title={t('interview.startEarly')}
              onPress={() => void exam.skipPreparation()}
              disabled={busy}
            />
          </>
        ) : null}

        {phase !== 'part2_cue' && phase !== 'part2_prep' ? (
          <>
            {/* Answers "can you hear me?". A candidate who has tapped answer
                and sees nothing move cannot tell whether they are being
                recorded or whether the app has hung — and on a timed exam that
                ambiguity costs them the question. */}
            <Waveform level={mic.level} active={mic.isRecording} />

            <Pressable
              onPress={() =>
                mic.isRecording
                  ? void mic.stopAndSend()
                  : void mic.startRecording()
              }
              disabled={busy}
              accessibilityRole="button"
              accessibilityLabel={
                mic.isRecording ? t('a11y.record.stop') : t('a11y.record.start')
              }
              style={[
                styles.recordButton,
                {
                  backgroundColor: mic.isRecording
                    ? theme.colors.error
                    : theme.colors.primary,
                  opacity: busy ? 0.5 : 1,
                },
              ]}
            >
              <Icon name="mic" size={32} color="onPrimary" />
            </Pressable>
            <AppText
              variant="bodySm"
              color="textSecondary"
              align="center"
              style={styles.hint}
            >
              {busy
                ? t('interview.sending')
                : mic.isRecording
                ? t('interview.listening')
                : t('interview.tapToAnswer')}
            </AppText>
          </>
        ) : null}
      </View>
    </ScreenContainer>
  );
};

const styles = StyleSheet.create({
  centred: {
    alignItems: 'center',
    flex: 1,
    gap: SPACING.md,
    justifyContent: 'center',
  },
  gap: { marginTop: SPACING.sm },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.sm,
  },
  timer: {
    alignItems: 'center',
    borderRadius: RADIUS.pill,
    flexDirection: 'row',
    gap: SPACING.xs,
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xs,
  },
  timerText: { marginLeft: SPACING.xs },
  prompt: { marginTop: SPACING.md },
  bullets: { gap: SPACING.xs, marginTop: SPACING.md },
  bullet: { marginLeft: SPACING.sm },
  error: { marginTop: SPACING.sm },
  controls: {
    alignItems: 'center',
    gap: SPACING.md,
    marginTop: 'auto',
    paddingVertical: SPACING.lg,
  },
  recordButton: {
    alignItems: 'center',
    borderRadius: RADIUS.pill,
    height: 88,
    justifyContent: 'center',
    width: 88,
  },
  hint: { paddingHorizontal: SPACING.lg },
});
