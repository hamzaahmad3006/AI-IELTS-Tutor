/** Reading practice screen (UI only). Logic in useReading. */

import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  BandBadge,
  Button,
  Card,
  DifficultySelector,
  MatchingHeadings,
  QuestionNavigator,
  TimerBar,
  Icon,
  Input,
  ScreenContainer,
  useTheme,
} from '@components';
import { getBandColor, RADIUS, SPACING } from '@constants';
import type { PracticeQuestion, ReadingPerQuestionResult } from '@models';
import { useReading } from './useReading';

export const Practice: React.FC = () => {
  const theme = useTheme();
  const {
    passage,
    isLoading,
    answers,
    answeredCount,
    isSubmitting,
    result,
    error,
    setAnswer,
    submit,
    tryAnother,
    onBack,
    difficulty,
    setDifficulty,
    answeredFlags,
    currentIndex,
    goToQuestion,
    secondsLeft,
    timerState,
    isWarning,
    startTimer,
    pauseTimer,
    resetTimer,
  } = useReading();

  if (isLoading || !passage) {
    return (
      <ScreenContainer>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      </ScreenContainer>
    );
  }

  // ---- Results view ----
  if (result) {
    const bandColor = getBandColor(result.band);
    return (
      <ScreenContainer scroll>
        <Header title="Reading Result" onBack={onBack} />
        <Card style={styles.section}>
          <View style={styles.resultRow}>
            <View>
              <AppText variant="labelMd" color="textSecondary">
                Estimated Band
              </AppText>
              <AppText variant="displayLg" style={{ color: bandColor }}>
                {result.band.toFixed(1)}
              </AppText>
              <AppText variant="bodyMd" color="textSecondary">
                {result.rawScore} / {result.totalQuestions} correct
              </AppText>
            </View>
            <BandBadge band={result.band} />
          </View>
        </Card>

        {result.perQuestion.map((pq, index) => (
          <ResultRow key={pq.questionId} index={index} pq={pq} />
        ))}

        <Button
          title="Try another passage"
          onPress={tryAnother}
          style={styles.section}
        />
      </ScreenContainer>
    );
  }

  // ---- Practice view ----
  // Matching-headings questions share one heading bank, so they are rendered
  // together rather than repeating the same five options four times.
  const matchingQuestions = passage.questions.filter(
    q => q.type === 'matching_headings',
  );
  const standardQuestions = passage.questions.filter(
    q => q.type !== 'matching_headings',
  );

  return (
    <ScreenContainer scroll>
      <Header title="Reading Practice" onBack={onBack} />

      <DifficultySelector
        value={difficulty}
        onChange={setDifficulty}
        served={passage?.difficulty ?? null}
        disabled={isLoading}
      />

      <TimerBar
        secondsLeft={secondsLeft}
        state={timerState}
        isWarning={isWarning}
        onStart={startTimer}
        onPause={pauseTimer}
        onReset={resetTimer}
        testID="reading-timer"
        expiredNote="Time is up. Your answers are kept — finish and submit when ready."
      />

      <Card style={styles.section} backgroundToken="cardAlt">
        <AppText variant="titleLg">{passage.title}</AppText>
        <AppText variant="bodyLg" color="textSecondary" style={styles.body}>
          {passage.body}
        </AppText>
      </Card>

      <AppText variant="headlineMd" style={styles.section}>
        Questions
      </AppText>

      <QuestionNavigator
        answered={answeredFlags}
        currentIndex={currentIndex}
        onSelect={goToQuestion}
      />

      {matchingQuestions.length > 0 ? (
        <MatchingHeadings
          headings={matchingQuestions[0].options ?? []}
          slots={matchingQuestions.map(q => ({
            id: q.id,
            // The paragraph is named in the prompt; the slot only needs that.
            label: q.prompt
              .replace(/^Choose the best heading for /, '')
              .replace(/\.$/, ''),
          }))}
          assignments={Object.fromEntries(
            matchingQuestions.map(q => [
              q.id,
              typeof answers[q.id] === 'string'
                ? (answers[q.id] as string)
                : undefined,
            ]),
          )}
          onAssign={(questionId, heading) =>
            setAnswer(questionId, heading ?? '')
          }
        />
      ) : null}

      {standardQuestions.map(q => {
        // Numbering follows the passage, not this filtered list, so the
        // navigator and the cards agree when both kinds are present.
        const questionIndex = passage.questions.indexOf(q);
        return (
          <QuestionCard
            key={q.id}
            index={questionIndex}
            question={q}
            value={answers[q.id]}
            isCurrent={questionIndex === currentIndex}
            onFocus={() => goToQuestion(questionIndex)}
            onChange={value => setAnswer(q.id, value)}
          />
        );
      })}

      {error ? (
        <AppText variant="labelMd" color="error" style={styles.section}>
          {error}
        </AppText>
      ) : null}

      <Button
        title={`Submit (${answeredCount}/${passage.questions.length})`}
        onPress={submit}
        loading={isSubmitting}
        disabled={answeredCount === 0}
        style={styles.section}
      />
    </ScreenContainer>
  );
};

const Header: React.FC<{ title: string; onBack: () => void }> = ({
  title,
  onBack,
}) => (
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

const QuestionCard: React.FC<{
  index: number;
  question: PracticeQuestion;
  value: string | string[] | undefined;
  isCurrent: boolean;
  onFocus: () => void;
  onChange: (value: string) => void;
}> = ({ index, question, value, isCurrent, onFocus, onChange }) => {
  const theme = useTheme();
  return (
    <Card
      style={[
        styles.qCard,
        // Ring the question the navigator points at, so tapping a number has a
        // visible effect even before the list is scrolled.
        isCurrent && { borderWidth: 2, borderColor: theme.colors.accent },
      ]}
      testID={`question-card-${index + 1}`}
    >
      <AppText variant="bodyMd" style={styles.qPrompt} onPress={onFocus}>
        {index + 1}. {question.prompt}
      </AppText>
      {question.options ? (
        question.options.map(option => {
          const selected = value === option;
          return (
            <Pressable
              key={option}
              onPress={() => onChange(option)}
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
              <View
                style={[
                  styles.radio,
                  {
                    borderColor: selected
                      ? theme.colors.primary
                      : theme.colors.outline,
                  },
                ]}
              >
                {selected ? (
                  <View
                    style={[
                      styles.radioDot,
                      { backgroundColor: theme.colors.primary },
                    ]}
                  />
                ) : null}
              </View>
              <AppText variant="bodyMd" style={styles.optionLabel}>
                {option}
              </AppText>
            </Pressable>
          );
        })
      ) : (
        <Input
          label=""
          value={typeof value === 'string' ? value : ''}
          onChangeText={onChange}
          placeholder="Type your answer"
          autoCapitalize="none"
        />
      )}
    </Card>
  );
};

const ResultRow: React.FC<{ index: number; pq: ReadingPerQuestionResult }> = ({
  index,
  pq,
}) => {
  const theme = useTheme();
  return (
    <Card style={styles.qCard}>
      <View style={styles.resultHead}>
        <View
          style={[
            styles.resultIcon,
            {
              backgroundColor: pq.correct
                ? theme.colors.suggestionHighlight
                : theme.colors.errorHighlight,
            },
          ]}
        >
          <Icon
            name={pq.correct ? 'check' : 'info'}
            size={16}
            color={pq.correct ? 'success' : 'error'}
          />
        </View>
        <AppText variant="labelMd" color={pq.correct ? 'success' : 'error'}>
          {/* The row never said which question it was about. */}
          {`Q${index + 1} · ${pq.correct ? 'Correct' : 'Incorrect'}`}
        </AppText>
      </View>
      <AppText variant="bodySm" color="textSecondary" style={styles.resultLine}>
        Your answer: {String(pq.submitted ?? '—')}
      </AppText>
      {!pq.correct ? (
        <AppText variant="bodySm" color="textSecondary">
          Correct answer: {String(pq.correctAnswer)}
        </AppText>
      ) : null}
      {pq.explanation ? (
        <AppText variant="bodySm" color="textMuted" style={styles.resultLine}>
          {pq.explanation}
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
  section: { marginTop: SPACING.lg },
  body: { marginTop: SPACING.sm },
  qCard: { marginTop: SPACING.md },
  qPrompt: { marginBottom: SPACING.sm },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    borderRadius: RADIUS.input,
    padding: SPACING.sm,
    marginBottom: SPACING.xs,
  },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: SPACING.sm,
  },
  radioDot: { width: 10, height: 10, borderRadius: 5 },
  optionLabel: { flex: 1 },
  resultRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  resultHead: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.xs,
  },
  resultIcon: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: SPACING.xs,
  },
  resultLine: { marginTop: SPACING.xxs },
});
