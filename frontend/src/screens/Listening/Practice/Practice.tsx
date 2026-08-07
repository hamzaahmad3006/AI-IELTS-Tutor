/** Listening practice screen (UI only). Logic in useListening. */

import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  BandBadge,
  EstimateNote,
  Button,
  Card,
  DifficultySelector,
  Icon,
  Input,
  ScreenContainer,
  useTheme,
} from '@components';
import { getBandColor, RADIUS, SPACING } from '@constants';
import type { ListeningPerQuestionResult, PracticeQuestion } from '@models';
import { useListening } from './useListening';

const formatDuration = (seconds: number): string => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
};

export const Practice: React.FC = () => {
  const theme = useTheme();
  const {
    clip,
    isLoading,
    answers,
    answeredCount,
    isPlaying,
    isSubmitting,
    result,
    error,
    playMode,
    setPlayMode,
    playsUsed,
    canPlay,
    togglePlayback,
    setAnswer,
    submit,
    tryAnother,
    onBack,
    difficulty,
    setDifficulty,
  } = useListening();

  if (isLoading || !clip) {
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
        <Header title="Listening Result" onBack={onBack} />
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
            <EstimateNote variant="short" />
          </View>
        </Card>

        {result.perQuestion.map((pq, index) => (
          <ResultRow key={pq.questionId} index={index} pq={pq} />
        ))}

        <Button
          title="Try another clip"
          onPress={tryAnother}
          style={styles.section}
        />
      </ScreenContainer>
    );
  }

  // ---- Practice view ----
  return (
    <ScreenContainer scroll>
      <Header title="Listening Practice" onBack={onBack} />

      <DifficultySelector
        value={difficulty}
        onChange={setDifficulty}
        served={clip?.difficulty ?? null}
        disabled={isLoading}
      />

      {/* Audio player */}
      <Card style={styles.section}>
        <AppText variant="titleLg">{clip.title}</AppText>
        <AppText variant="bodySm" color="textSecondary" style={styles.clipMeta}>
          {clip.accent ? `${clip.accent} · ` : ''}
          {formatDuration(clip.durationSec)} · {clip.difficulty}
        </AppText>
        <View style={styles.playerRow}>
          <Pressable
            onPress={togglePlayback}
            disabled={!canPlay && !isPlaying}
            accessibilityRole="button"
            accessibilityState={{ disabled: !canPlay && !isPlaying }}
            accessibilityLabel={isPlaying ? 'Pause' : 'Play'}
            testID="play-button"
          >
            <View
              style={[
                styles.playButton,
                {
                  backgroundColor: theme.colors.accent,
                  opacity: !canPlay && !isPlaying ? 0.4 : 1,
                },
              ]}
            >
              <Icon
                name={isPlaying ? 'pause' : 'play'}
                size={26}
                color="onAccent"
              />
            </View>
          </Pressable>
          <View style={styles.playerBar}>
            <View
              style={[
                styles.playerTrack,
                { backgroundColor: theme.colors.containerHighest },
              ]}
            />
            <AppText
              variant="labelSm"
              color="textMuted"
              style={styles.playerHint}
              testID="player-hint"
            >
              {isPlaying
                ? 'Playing…'
                : !canPlay
                ? 'Played once — the exam does not replay the recording'
                : 'Tap play to listen'}
            </AppText>
          </View>
        </View>

        <View style={styles.modeRow}>
          <AppText variant="labelSm" color="textMuted">
            {playMode === 'exam'
              ? `Exam rules · ${playsUsed}/1 play used`
              : 'Practice · replay allowed'}
          </AppText>
          <Pressable
            onPress={() =>
              setPlayMode(playMode === 'exam' ? 'practice' : 'exam')
            }
            accessibilityRole="button"
            testID="play-mode-toggle"
          >
            <AppText variant="labelSm" color="primary">
              {playMode === 'exam' ? 'Allow replay' : 'Use exam rules'}
            </AppText>
          </Pressable>
        </View>
      </Card>

      <View style={styles.progressRow}>
        <AppText variant="titleLg">Questions</AppText>
        <AppText variant="labelMd" color="textSecondary">
          {answeredCount} / {clip.questions.length} answered
        </AppText>
      </View>

      {clip.questions.map((question, index) => (
        <QuestionCard
          key={question.id}
          index={index}
          question={question}
          value={answers[question.id]}
          onChange={value => setAnswer(question.id, value)}
        />
      ))}

      {error ? (
        <AppText variant="labelMd" color="error" style={styles.error}>
          {error}
        </AppText>
      ) : null}

      <Button
        title="Submit answers"
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
  onChange: (value: string) => void;
}> = ({ index, question, value, onChange }) => {
  const theme = useTheme();
  return (
    <Card style={styles.qCard}>
      <AppText variant="bodyMd" style={styles.qPrompt}>
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

const ResultRow: React.FC<{
  index: number;
  pq: ListeningPerQuestionResult;
}> = ({ index, pq }) => {
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
          Question {index + 1} · {pq.correct ? 'Correct' : 'Incorrect'}
        </AppText>
      </View>
      <AppText variant="bodySm" color="textSecondary" style={styles.resultLine}>
        Your answer: {String(pq.submitted ?? '—')}
      </AppText>
      {!pq.correct ? (
        <AppText variant="bodySm" color="textPrimary" style={styles.resultLine}>
          Correct answer: {String(pq.correctAnswer)}
        </AppText>
      ) : null}
      {pq.explanation ? (
        <AppText
          variant="bodySm"
          color="textSecondary"
          style={styles.resultLine}
        >
          {pq.explanation}
        </AppText>
      ) : null}
      {pq.answerTimestamp ? (
        <View style={styles.timestampRow}>
          <Icon name="timer" size={14} color="primary" />
          <AppText
            variant="labelSm"
            color="primary"
            style={styles.timestampText}
          >
            Heard at {pq.answerTimestamp}
          </AppText>
        </View>
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
  clipMeta: { marginTop: SPACING.xxs },
  modeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: SPACING.sm,
  },
  playerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: SPACING.md,
  },
  playButton: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  playerBar: { flex: 1, marginLeft: SPACING.md },
  playerTrack: { height: 6, borderRadius: RADIUS.pill },
  playerHint: { marginTop: SPACING.xs },
  progressRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: SPACING.lg,
    marginBottom: SPACING.xs,
  },
  qCard: { marginTop: SPACING.md },
  qPrompt: { marginBottom: SPACING.sm },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: RADIUS.md,
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
  },
  radioDot: { width: 10, height: 10, borderRadius: 5 },
  optionLabel: { marginLeft: SPACING.sm, flex: 1 },
  error: { marginTop: SPACING.md },
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
    width: 26,
    height: 26,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: SPACING.xs,
  },
  resultLine: { marginTop: SPACING.xxs },
  timestampRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: SPACING.xs,
  },
  timestampText: { marginLeft: SPACING.xxs },
});
