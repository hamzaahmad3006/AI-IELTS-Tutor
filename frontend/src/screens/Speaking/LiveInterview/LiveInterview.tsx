/** Live voice interview with the AI examiner (UI only). Logic in useLiveInterview. */

import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import { useRoute, type RouteProp } from '@react-navigation/native';
import {
  AppText,
  Button,
  Card,
  Icon,
  ScreenContainer,
  useTheme,
} from '@components';
import { RADIUS, SPACING } from '@constants';
import type { RootStackParamList } from '@models';
import { useLiveInterview, type Phase } from './useLiveInterview';

/** One line of plain English per state. The screen should read on video. */
const LABELS: Record<Phase, string> = {
  idle: 'Ready when you are',
  connecting: 'Connecting to your examiner…',
  waiting: 'Connected — the examiner is about to speak',
  examinerSpeaking: 'Examiner is speaking',
  listening: 'Listening — speak your answer',
  thinking: 'Thinking about your answer…',
  finished: 'Interview complete',
  failed: 'Something went wrong',
};

export const LiveInterview: React.FC = () => {
  const theme = useTheme();
  const route = useRoute<RouteProp<RootStackParamList, 'LiveInterview'>>();
  const sessionId = route.params?.sessionId ?? '';

  const {
    phase,
    status,
    examinerText,
    lastAnswer,
    error,
    isMuted,
    start,
    end,
    toggleMute,
  } = useLiveInterview(sessionId);

  const isLive =
    phase === 'waiting' ||
    phase === 'examinerSpeaking' ||
    phase === 'listening' ||
    phase === 'thinking';

  // The one visual cue that carries on video: who currently holds the turn.
  const accent =
    phase === 'listening'
      ? theme.colors.accent
      : phase === 'examinerSpeaking'
      ? theme.colors.primary
      : theme.colors.outline;

  return (
    <ScreenContainer scroll>
      <AppText variant="headlineMobile" style={styles.title}>
        AI Interviewer
      </AppText>
      <AppText variant="bodyMd" color="textSecondary" style={styles.subtitle}>
        A real conversation — the examiner listens, understands, and asks the
        next question based on what you said.
      </AppText>

      {/* Status. Deliberately the largest thing on screen: it is what makes a
          silent video legible. */}
      {/* A reconnect is the one thing that looks identical to a hang: the orb
          keeps its last state and nothing moves. Saying so is the difference
          between "wait a moment" and "this is broken". */}
      {status === 'reconnecting' ? (
        <AppText variant="labelMd" color="warning" style={styles.reconnecting}>
          Reconnecting…
        </AppText>
      ) : null}

      <Card style={styles.stage}>
        <View style={[styles.orb, { borderColor: accent }]}>
          {phase === 'thinking' || phase === 'connecting' ? (
            <ActivityIndicator size="large" color={accent} />
          ) : (
            <Icon
              name={phase === 'listening' ? 'mic' : 'speaking'}
              size={44}
              color={phase === 'listening' ? 'accent' : 'primary'}
            />
          )}
        </View>
        <AppText variant="titleLg" align="center" style={styles.phase}>
          {LABELS[phase]}
        </AppText>
      </Card>

      {examinerText ? (
        <View
          style={[
            styles.bubble,
            { backgroundColor: theme.colors.accentContainer },
          ]}
        >
          <AppText variant="labelSm" color="onAccentContainer">
            EXAMINER
          </AppText>
          <AppText
            variant="bodyLg"
            color="onAccentContainer"
            style={styles.bubbleText}
          >
            {examinerText}
          </AppText>
        </View>
      ) : null}

      {lastAnswer ? (
        <Card style={styles.answer}>
          <AppText variant="labelSm" color="textMuted">
            WHAT WE HEARD
          </AppText>
          <AppText variant="bodyMd" style={styles.bubbleText}>
            {lastAnswer}
          </AppText>
        </Card>
      ) : null}

      {error ? (
        <AppText variant="labelMd" color="error" style={styles.error}>
          {error}
        </AppText>
      ) : null}

      {isLive ? (
        <View style={styles.controls}>
          <Pressable onPress={() => void toggleMute()} style={styles.control}>
            <View
              style={[
                styles.controlCircle,
                { backgroundColor: theme.colors.primaryContainer },
              ]}
            >
              <Icon
                name="mic"
                size={24}
                color={isMuted ? 'error' : 'primary'}
              />
            </View>
            <AppText variant="labelSm" color="textSecondary">
              {isMuted ? 'Unmute' : 'Mute'}
            </AppText>
          </Pressable>

          <Pressable onPress={() => void end()} style={styles.control}>
            <View
              style={[
                styles.controlCircle,
                { backgroundColor: theme.colors.errorHighlight },
              ]}
            >
              <Icon name="end-call" size={24} color="error" />
            </View>
            <AppText variant="labelSm" color="error">
              End
            </AppText>
          </Pressable>
        </View>
      ) : (
        <Button
          title={
            phase === 'finished' ? 'Start another interview' : 'Start interview'
          }
          icon="mic"
          onPress={() => void start()}
          style={styles.start}
        />
      )}
    </ScreenContainer>
  );
};

const styles = StyleSheet.create({
  title: { marginTop: SPACING.md },
  subtitle: { marginTop: SPACING.xs, marginBottom: SPACING.lg },
  stage: { alignItems: 'center', paddingVertical: SPACING.xl },
  orb: {
    width: 132,
    height: 132,
    borderRadius: 66,
    borderWidth: 3,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: SPACING.lg,
  },
  phase: { marginTop: SPACING.xs },
  reconnecting: { marginBottom: SPACING.sm },
  bubble: {
    marginTop: SPACING.lg,
    borderRadius: RADIUS.card,
    padding: SPACING.md,
  },
  bubbleText: { marginTop: SPACING.xxs },
  answer: { marginTop: SPACING.md },
  error: { marginTop: SPACING.md },
  start: { marginTop: SPACING.xl },
  controls: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: SPACING.xl,
  },
  control: { alignItems: 'center', marginHorizontal: SPACING.lg },
  controlCircle: {
    width: 60,
    height: 60,
    borderRadius: 30,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: SPACING.xs,
  },
});
