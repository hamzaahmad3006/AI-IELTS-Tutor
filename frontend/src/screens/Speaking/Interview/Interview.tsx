/** Speaking interview (UI only). Logic in useInterview. */

import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import {
  AppText,
  Card,
  Icon,
  ScreenContainer,
  useTheme,
} from '../../../components';
import { PALETTE, RADIUS, SPACING } from '../../../constants';
import type { TranscriptEntry, TranscriptToken } from '../../../types';
import { useInterview } from './useInterview';

export const Interview: React.FC = () => {
  const theme = useTheme();
  const {
    session,
    isLoading,
    isMuted,
    isPaused,
    elapsedLabel,
    toggleMute,
    togglePause,
    endCall,
  } = useInterview();

  if (isLoading || !session) {
    return (
      <ScreenContainer>
        <View style={styles.loader}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
          <AppText variant="bodyMd" color="textSecondary" style={styles.connecting}>
            Connecting to your AI examiner...
          </AppText>
        </View>
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={endCall} hitSlop={8}>
          <Icon name="back" size={24} color="primary" />
        </Pressable>
        <AppText variant="titleLg" color="primary">
          Speaking · Part {session.part}
        </AppText>
        <View style={[styles.timer, { backgroundColor: theme.colors.primaryContainer }]}>
          <Icon name="timer" size={16} color="error" />
          <AppText variant="labelMd" style={styles.timerText}>
            {elapsedLabel}
          </AppText>
        </View>
      </View>

      {/* Examiner prompt */}
      <AppText variant="headlineMd" color="primary" align="center" style={styles.examiner}>
        {session.examinerName}
      </AppText>
      <AppText variant="bodyLg" color="textSecondary" align="center" style={styles.prompt}>
        {session.currentPrompt}
      </AppText>

      {/* Live transcript */}
      <Card style={styles.transcriptCard}>
        <View style={styles.transcriptHead}>
          <View style={styles.transcriptTitle}>
            <Icon name="speaking" size={18} color="accent" />
            <AppText variant="labelMd" color="textSecondary" style={styles.transcriptLabel}>
              LIVE TRANSCRIPT
            </AppText>
          </View>
          <View style={[styles.confidence, { backgroundColor: PALETTE.tealContainer }]}>
            <AppText variant="labelSm" style={styles.confidenceText}>
              Confidence Boost: {session.confidenceBoost}%
            </AppText>
          </View>
        </View>

        <View style={styles.transcriptBody}>
          {session.transcript.map((entry) => (
            <TranscriptLine key={entry.id} entry={entry} />
          ))}
        </View>
      </Card>

      {/* Call controls */}
      <View style={styles.controls}>
        <Pressable style={styles.sideControl} onPress={toggleMute}>
          <View
            style={[
              styles.controlCircle,
              { backgroundColor: theme.colors.primaryContainer },
            ]}
          >
            <Icon name="mic" size={24} color={isMuted ? 'error' : 'primary'} />
          </View>
          <AppText variant="labelSm" color="textSecondary" style={styles.controlLabel}>
            {isMuted ? 'Unmute' : 'Mute'}
          </AppText>
        </Pressable>

        <Pressable onPress={togglePause}>
          <LinearGradient
            colors={[PALETTE.teal400, PALETTE.teal600]}
            style={styles.mainControl}
          >
            <Icon name={isPaused ? 'play' : 'pause'} size={30} color="textInverse" />
          </LinearGradient>
        </Pressable>

        <Pressable style={styles.sideControl} onPress={endCall}>
          <View style={[styles.controlCircle, { backgroundColor: theme.colors.errorHighlight }]}>
            <Icon name="end-call" size={24} color="error" />
          </View>
          <AppText variant="labelSm" color="error" style={styles.controlLabel}>
            End Call
          </AppText>
        </Pressable>
      </View>
    </ScreenContainer>
  );
};

const TranscriptLine: React.FC<{ entry: TranscriptEntry }> = ({ entry }) => {
  const theme = useTheme();
  if (entry.speaker === 'examiner') {
    return (
      <AppText variant="bodyLg" color="textMuted" style={styles.examinerLine}>
        {entry.tokens.map((t) => t.text).join('')}
      </AppText>
    );
  }
  if (!entry.isFinal) {
    return (
      <View style={[styles.pendingLine, { borderLeftColor: theme.colors.primary }]}>
        <AppText variant="bodyLg" color="primary">
          {entry.tokens.map((t) => t.text).join('')}
        </AppText>
      </View>
    );
  }
  return (
    <AppText variant="bodyLg" style={styles.learnerLine}>
      {entry.tokens.map((token, index) => (
        <TokenSpan key={index} token={token} />
      ))}
    </AppText>
  );
};

const TokenSpan: React.FC<{ token: TranscriptToken }> = ({ token }) => {
  const theme = useTheme();
  if (token.kind === 'strong') {
    return (
      <AppText variant="bodyLg" style={{ backgroundColor: PALETTE.tealContainer }}>
        {token.text}
      </AppText>
    );
  }
  if (token.kind === 'suggestion') {
    return (
      <AppText
        variant="bodyLg"
        color="primary"
        style={{ backgroundColor: theme.colors.suggestionHighlight }}
      >
        {token.text}
      </AppText>
    );
  }
  return <AppText variant="bodyLg">{token.text}</AppText>;
};

const styles = StyleSheet.create({
  loader: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  connecting: { marginTop: SPACING.md },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: SPACING.md,
  },
  timer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xxs,
    borderRadius: RADIUS.pill,
  },
  timerText: { marginLeft: SPACING.xxs },
  examiner: { marginTop: SPACING.lg },
  prompt: { marginTop: SPACING.sm, marginBottom: SPACING.lg },
  transcriptCard: { flex: 1 },
  transcriptHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.md,
  },
  transcriptTitle: { flexDirection: 'row', alignItems: 'center' },
  transcriptLabel: { marginLeft: SPACING.xs },
  confidence: {
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xxs,
    borderRadius: RADIUS.pill,
  },
  confidenceText: { color: PALETTE.tealDeep },
  transcriptBody: { flex: 1 },
  examinerLine: { fontStyle: 'italic', marginBottom: SPACING.md },
  learnerLine: { marginBottom: SPACING.md },
  pendingLine: {
    borderLeftWidth: 3,
    paddingLeft: SPACING.sm,
    marginTop: SPACING.xs,
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingVertical: SPACING.lg,
  },
  sideControl: { alignItems: 'center' },
  controlCircle: {
    width: 60,
    height: 60,
    borderRadius: 30,
    alignItems: 'center',
    justifyContent: 'center',
  },
  controlLabel: { marginTop: SPACING.xs },
  mainControl: {
    width: 84,
    height: 84,
    borderRadius: 42,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
