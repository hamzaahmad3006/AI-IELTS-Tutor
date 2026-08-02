/** Placement diagnostic (UI only). Logic in useDiagnostic. */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  BandBadge,
  Button,
  Card,
  EmptyState,
  Input,
  ScreenContainer,
  SkeletonCard,
  useTheme,
} from '../../../components';
import { getBandColor, RADIUS, SPACING } from '../../../constants';
import type { DiagnosticQuestion, DiagnosticResult } from '../../../types';
import { STEP_LABELS, STEPS, useDiagnostic } from './useDiagnostic';

export const Diagnostic: React.FC = () => {
  const theme = useTheme();
  const {
    set,
    isLoading,
    error,
    step,
    stepIndex,
    totalSteps,
    isLastStep,
    readingAnswers,
    listeningAnswers,
    writingText,
    speakingText,
    setReadingAnswer,
    setListeningAnswer,
    setWritingText,
    setSpeakingText,
    next,
    back,
    isSubmitting,
    result,
    submit,
    finish,
  } = useDiagnostic();

  if (isLoading) {
    return (
      <ScreenContainer scroll>
        <SkeletonCard lines={2} />
        <SkeletonCard lines={4} />
      </ScreenContainer>
    );
  }

  if (result) {
    return <ResultView result={result} onFinish={finish} />;
  }

  if (!set) {
    return (
      <ScreenContainer>
        <EmptyState
          variant="error"
          title="Placement test unavailable"
          message={error ?? 'You can set your target band without it.'}
          actionLabel="Continue"
          onAction={finish}
        />
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer scroll>
      <View style={styles.progressRow}>
        {STEPS.map((name, index) => (
          <View
            key={name}
            style={[
              styles.progressBar,
              {
                backgroundColor:
                  index <= stepIndex
                    ? theme.colors.primary
                    : theme.colors.containerHighest,
              },
            ]}
          />
        ))}
      </View>
      <AppText variant="labelSm" color="textMuted">
        {`Step ${stepIndex + 1} of ${totalSteps} · ${STEP_LABELS[step]}`}
      </AppText>

      <AppText variant="headlineMobile" style={styles.title}>
        Where are you starting from?
      </AppText>
      <AppText variant="bodySm" color="textSecondary" style={styles.note}>
        {set.note}
      </AppText>

      {step === 'reading' ? (
        <>
          <Card style={styles.section} backgroundToken="cardAlt">
            <AppText variant="labelMd" color="textSecondary">
              {set.reading.title.toUpperCase()}
            </AppText>
            <AppText variant="bodyMd" style={styles.body}>
              {set.reading.body}
            </AppText>
          </Card>
          {set.reading.questions.map((question) => (
            <QuestionBlock
              key={question.id}
              question={question}
              value={readingAnswers[question.id]}
              onChange={(value) => setReadingAnswer(question.id, value)}
            />
          ))}
        </>
      ) : null}

      {step === 'listening' ? (
        <>
          <Card style={styles.section} backgroundToken="cardAlt">
            <AppText variant="labelMd" color="textSecondary">
              {set.listening.title.toUpperCase()}
            </AppText>
            {/* Said plainly rather than showing a play button that does
                nothing: audio playback needs a native player that is not
                wired yet. */}
            <AppText variant="bodySm" color="textSecondary" style={styles.body}>
              Audio playback is not available yet, so you can skip this section
              and it will simply not be estimated.
            </AppText>
          </Card>
          {set.listening.questions.map((question) => (
            <QuestionBlock
              key={question.id}
              question={question}
              value={listeningAnswers[question.id]}
              onChange={(value) => setListeningAnswer(question.id, value)}
            />
          ))}
        </>
      ) : null}

      {step === 'writing' ? (
        <FreeTextStep
          prompt={set.writing.prompt}
          minWords={set.writing.minWords}
          value={writingText}
          onChange={setWritingText}
          placeholder="Write your response…"
          testID="diagnostic-writing"
        />
      ) : null}

      {step === 'speaking' ? (
        <FreeTextStep
          prompt={set.speaking.prompt}
          minWords={set.speaking.minWords}
          value={speakingText}
          onChange={setSpeakingText}
          placeholder="Type what you would say…"
          testID="diagnostic-speaking"
        />
      ) : null}

      {error ? (
        <AppText variant="labelMd" color="error" style={styles.section}>
          {error}
        </AppText>
      ) : null}

      <View style={styles.actions}>
        {stepIndex > 0 ? (
          <Button
            title="Back"
            variant="secondary"
            fullWidth={false}
            onPress={back}
            testID="diagnostic-back"
          />
        ) : null}
        <Button
          title={
            isLastStep ? (isSubmitting ? 'Scoring…' : 'See my level') : 'Next'
          }
          onPress={isLastStep ? submit : next}
          disabled={isSubmitting}
          testID="diagnostic-next"
          style={styles.grow}
        />
      </View>

      <Pressable onPress={finish} testID="diagnostic-skip">
        <AppText variant="labelMd" color="textMuted" align="center">
          Skip the placement test
        </AppText>
      </Pressable>
    </ScreenContainer>
  );
};

const QuestionBlock: React.FC<{
  question: DiagnosticQuestion;
  value: string | undefined;
  onChange: (value: string) => void;
}> = ({ question, value, onChange }) => {
  const theme = useTheme();
  return (
    <Card style={styles.section} testID={`diagnostic-q-${question.id}`}>
      <AppText variant="bodyMd">{question.prompt}</AppText>
      {question.options ? (
        question.options.map((option) => {
          const selected = value === option;
          return (
            <Pressable
              key={option}
              onPress={() => onChange(option)}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              testID={`option-${question.id}-${option}`}
              style={[
                styles.option,
                {
                  borderColor: selected
                    ? theme.colors.primary
                    : theme.colors.border,
                  backgroundColor: selected
                    ? theme.colors.primaryContainer
                    : theme.colors.card,
                },
              ]}
            >
              <AppText variant="bodySm">{option}</AppText>
            </Pressable>
          );
        })
      ) : (
        <Input
          label=""
          value={value ?? ''}
          onChangeText={onChange}
          placeholder="Your answer"
        />
      )}
    </Card>
  );
};

const FreeTextStep: React.FC<{
  prompt: string;
  minWords: number;
  value: string;
  onChange: (text: string) => void;
  placeholder: string;
  testID: string;
}> = ({ prompt, minWords, value, onChange, placeholder, testID }) => {
  const words = value.trim() ? value.trim().split(/\s+/).length : 0;
  return (
    <>
      <Card style={styles.section} backgroundToken="cardAlt">
        <AppText variant="bodyLg">{prompt}</AppText>
      </Card>
      <View style={styles.countRow}>
        <AppText variant="labelSm" color="textMuted">
          {/* Below the minimum it is not scored at all, so the threshold is
              shown rather than letting someone write 10 words and wonder why
              nothing came back. */}
          {`${words} / ${minWords} words minimum`}
        </AppText>
      </View>
      <Input
        label=""
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        multiline
        autoCapitalize="sentences"
        testID={testID}
      />
    </>
  );
};

const ResultView: React.FC<{
  result: DiagnosticResult;
  onFinish: () => void;
}> = ({ result, onFinish }) => (
  <ScreenContainer scroll>
    <AppText variant="headlineMobile" style={styles.title}>
      Your starting point
    </AppText>

    <Card style={styles.section} testID="diagnostic-result">
      <View style={styles.overallRow}>
        <View>
          <AppText variant="labelMd" color="textSecondary">
            ESTIMATED OVERALL
          </AppText>
          <AppText
            variant="displayLg"
            style={{ color: getBandColor(result.overallBand ?? 0) }}
          >
            {result.overallBand !== null ? result.overallBand.toFixed(1) : '—'}
          </AppText>
          {result.cefrLevel ? (
            <AppText variant="labelMd" color="primary">
              {`CEFR ${result.cefrLevel}`}
            </AppText>
          ) : null}
        </View>
        {result.overallBand !== null ? (
          <BandBadge band={result.overallBand} />
        ) : null}
      </View>
      <AppText variant="bodySm" color="textSecondary" style={styles.body}>
        {result.cefrDescription}
      </AppText>
    </Card>

    <Card style={styles.section}>
      <AppText variant="labelMd" color="textSecondary">
        BY MODULE
      </AppText>
      {result.baselines.map((baseline) => (
        <View key={baseline.module} style={styles.baselineRow}>
          <View style={styles.grow}>
            <AppText variant="bodyMd">
              {baseline.module.charAt(0).toUpperCase() + baseline.module.slice(1)}
            </AppText>
            <AppText variant="labelSm" color="textMuted">
              {baseline.detail}
            </AppText>
          </View>
          <AppText
            variant="labelMd"
            style={{
              color:
                baseline.band !== null ? getBandColor(baseline.band) : undefined,
            }}
            color={baseline.band === null ? 'textMuted' : undefined}
          >
            {baseline.band !== null ? baseline.band.toFixed(1) : 'Not measured'}
          </AppText>
        </View>
      ))}
    </Card>

    <AppText variant="bodyMd" color="textSecondary" style={styles.section}>
      {result.summary}
    </AppText>

    <Button title="Continue" onPress={onFinish} style={styles.section} />
  </ScreenContainer>
);

const styles = StyleSheet.create({
  progressRow: { flexDirection: 'row', gap: 4, marginBottom: SPACING.sm },
  progressBar: { flex: 1, height: 4, borderRadius: 2 },
  title: { marginTop: SPACING.sm, marginBottom: SPACING.xs },
  note: { marginBottom: SPACING.sm },
  section: { marginTop: SPACING.md },
  body: { marginTop: SPACING.xs },
  option: {
    borderWidth: 1,
    borderRadius: RADIUS.md,
    padding: SPACING.sm,
    marginTop: SPACING.sm,
  },
  countRow: { alignItems: 'flex-end', marginTop: SPACING.sm },
  actions: {
    flexDirection: 'row',
    gap: SPACING.sm,
    marginTop: SPACING.lg,
    marginBottom: SPACING.sm,
  },
  grow: { flex: 1 },
  overallRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  baselineRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    marginTop: SPACING.sm,
  },
});
