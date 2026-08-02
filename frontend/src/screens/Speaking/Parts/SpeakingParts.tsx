/** Part 1 / Part 3 question runner (UI only). Logic in useSpeakingParts. */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  BandBadge,
  Button,
  Card,
  EmptyState,
  Icon,
  Input,
  QuestionNavigator,
  ScreenContainer,
  SkeletonCard,
} from '../../../components';
import { getBandColor, SPACING } from '../../../constants';
import { useSpeakingParts } from './useSpeakingParts';

export const SpeakingParts: React.FC = () => {
  const {
    part,
    set,
    isLoading,
    index,
    answers,
    currentAnswer,
    wordCount,
    canAdvance,
    isLastQuestion,
    answeredCount,
    isSubmitting,
    result,
    error,
    setAnswer,
    goTo,
    nextQuestion,
    submit,
    onBack,
    continueAfterResult,
  } = useSpeakingParts();

  if (isLoading) {
    return (
      <ScreenContainer scroll>
        <SkeletonCard lines={2} />
        <SkeletonCard lines={4} />
      </ScreenContainer>
    );
  }

  if (!set) {
    return (
      <ScreenContainer>
        <EmptyState
          variant="error"
          title="Could not load questions"
          message={error ?? 'Please try again.'}
          actionLabel="Go back"
          onAction={onBack}
        />
      </ScreenContainer>
    );
  }

  if (result) {
    return (
      <ScreenContainer scroll>
        <Header part={part} topic={set.topic} onBack={onBack} />
        <Card style={styles.section} testID="parts-result">
          <AppText variant="labelMd" color="textSecondary">
            BAND FOR THIS RUN
          </AppText>
          <View style={styles.bandRow}>
            <AppText
              variant="displayLg"
              style={{ color: getBandColor(result.overallBand ?? 0) }}
            >
              {result.overallBand !== null ? result.overallBand.toFixed(1) : '—'}
            </AppText>
            {result.overallBand !== null ? (
              <BandBadge band={result.overallBand} />
            ) : null}
          </View>
          {result.feedbackSummary ? (
            <AppText variant="bodyMd" color="textSecondary">
              {result.feedbackSummary}
            </AppText>
          ) : null}
        </Card>
        <Button title="Continue" onPress={continueAfterResult} style={styles.section} />
      </ScreenContainer>
    );
  }

  const question = set.questions[index];

  return (
    <ScreenContainer scroll>
      <Header part={part} topic={set.topic} onBack={onBack} />

      <Card style={styles.section} backgroundToken="cardAlt">
        <AppText variant="labelMd" color="textSecondary">
          HOW TO ANSWER
        </AppText>
        <AppText variant="bodySm" color="textSecondary" style={styles.guidance}>
          {set.guidance}
        </AppText>
      </Card>

      <QuestionNavigator
        answered={set.questions.map(
          (q) => (answers[q.id] ?? '').trim().length > 0,
        )}
        currentIndex={index}
        onSelect={goTo}
      />

      <Card style={styles.section} testID={`parts-question-${index + 1}`}>
        <AppText variant="labelSm" color="textMuted">
          {`QUESTION ${index + 1} OF ${set.questions.length}`}
        </AppText>
        <AppText variant="bodyLg" style={styles.question}>
          {question?.question ?? ''}
        </AppText>
      </Card>

      <View style={styles.answerHead}>
        <AppText variant="titleLg">Your answer</AppText>
        <AppText variant="labelMd" color={canAdvance ? 'success' : 'textMuted'}>
          {`${wordCount} words`}
        </AppText>
      </View>

      <Input
        label=""
        value={currentAnswer}
        onChangeText={setAnswer}
        placeholder="Answer as you would speak…"
        multiline
        autoCapitalize="sentences"
        testID="parts-answer-input"
      />

      {error ? (
        <AppText variant="labelMd" color="error" style={styles.section}>
          {error}
        </AppText>
      ) : null}

      {isLastQuestion ? (
        <Button
          title={isSubmitting ? 'Scoring…' : 'Finish and score'}
          onPress={submit}
          disabled={isSubmitting || answeredCount === 0}
          style={styles.section}
          testID="parts-submit"
        />
      ) : (
        <Button
          title="Next question"
          onPress={nextQuestion}
          disabled={!canAdvance}
          style={styles.section}
          testID="parts-next"
        />
      )}
    </ScreenContainer>
  );
};

const Header: React.FC<{ part: number; topic: string; onBack: () => void }> = ({
  part,
  topic,
  onBack,
}) => (
  <View style={styles.header}>
    <Pressable onPress={onBack} accessibilityRole="button" accessibilityLabel="Back">
      <Icon name="back" size={22} color="primary" />
    </Pressable>
    <View style={styles.headerText}>
      <AppText variant="titleLg">{`Speaking Part ${part}`}</AppText>
      <AppText variant="labelSm" color="textMuted">
        {topic}
      </AppText>
    </View>
  </View>
);

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    marginBottom: SPACING.md,
  },
  headerText: { flex: 1 },
  section: { marginTop: SPACING.md },
  guidance: { marginTop: SPACING.xs },
  question: { marginTop: SPACING.xs },
  answerHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: SPACING.md,
    marginBottom: SPACING.sm,
  },
  bandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginVertical: SPACING.sm,
  },
});
