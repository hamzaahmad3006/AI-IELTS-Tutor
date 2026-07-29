/** Daily AI Coach screen (UI only). Logic in useCoach. */

import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  Button,
  Card,
  Icon,
  ProgressBar,
  ScreenContainer,
  useTheme,
} from '../../../components';
import { PALETTE, RADIUS, SPACING, type IconName } from '../../../constants';
import type {
  AdaptiveDifficultyItem,
  IeltsModule,
  Recommendation,
} from '../../../types';
import { useCoach } from './useCoach';

const MODULE_LABELS: Record<IeltsModule, string> = {
  speaking: 'Speaking',
  writing: 'Writing',
  reading: 'Reading',
  listening: 'Listening',
};

const MODULE_ICONS: Record<IeltsModule, IconName> = {
  speaking: 'mic',
  writing: 'writing',
  reading: 'reading',
  listening: 'listening',
};

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: PALETTE.success,
  medium: PALETTE.warning,
  hard: PALETTE.coral,
};

export const Coach: React.FC = () => {
  const theme = useTheme();
  const {
    recommendations,
    message,
    difficulty,
    isLoading,
    error,
    reload,
    openModule,
    openVocabulary,
    openGrammar,
  } = useCoach();

  if (isLoading) {
    return (
      <ScreenContainer>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      </ScreenContainer>
    );
  }

  if (error) {
    return (
      <ScreenContainer>
        <View style={styles.center}>
          <Icon name="info" size={40} color="error" />
          <AppText variant="bodyMd" color="textSecondary" align="center" style={styles.errorText}>
            {error}
          </AppText>
          <Button title="Retry" onPress={reload} fullWidth={false} />
        </View>
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer scroll>
      <AppText variant="headlineMobile" style={styles.title}>
        Your AI Coach
      </AppText>

      {/* Coach message */}
      <View style={[styles.coachBanner, { backgroundColor: PALETTE.tealContainer }]}>
        <View style={[styles.coachIcon, { backgroundColor: PALETTE.teal }]}>
          <Icon name="coach" size={22} color="textInverse" />
        </View>
        <AppText variant="bodyMd" style={styles.coachMessage}>
          {message}
        </AppText>
      </View>

      {/* Recommendations */}
      {recommendations.length > 0 ? (
        <>
          <AppText variant="titleLg" style={styles.sectionTitle}>
            Recommended focus
          </AppText>
          {recommendations.map((rec) => (
            <RecommendationCard
              key={`${rec.module}-${rec.tag}`}
              rec={rec}
              onPress={() => openModule(rec.module)}
            />
          ))}
        </>
      ) : (
        <Card style={styles.section} backgroundToken="cardAlt">
          <AppText variant="titleLg">Nothing to fix yet</AppText>
          <AppText variant="bodyMd" color="textSecondary" style={styles.emptyBody}>
            Complete a few practice sessions and your coach will pinpoint exactly
            what to work on.
          </AppText>
        </Card>
      )}

      <Button
        title="Review vocabulary"
        variant="secondary"
        icon="arrow-right"
        onPress={openVocabulary}
        style={styles.section}
      />

      <Button
        title="Grammar lessons"
        variant="secondary"
        icon="arrow-right"
        onPress={openGrammar}
        style={styles.section}
      />

      {/* Adaptive difficulty */}
      <AppText variant="titleLg" style={styles.sectionTitle}>
        Your current level
      </AppText>
      {difficulty.map((item) => (
        <DifficultyRow key={item.module} item={item} />
      ))}
    </ScreenContainer>
  );
};

const RecommendationCard: React.FC<{
  rec: Recommendation;
  onPress: () => void;
}> = ({ rec, onPress }) => {
  const theme = useTheme();
  return (
    <Pressable onPress={onPress}>
      <Card style={styles.recCard}>
        <View style={styles.recHead}>
          <View style={[styles.recIcon, { backgroundColor: theme.colors.primaryContainer }]}>
            <Icon name={MODULE_ICONS[rec.module]} size={20} color="primary" />
          </View>
          <View style={styles.recTitleWrap}>
            <AppText variant="titleLg">{rec.title}</AppText>
            <AppText variant="labelSm" color="textMuted">
              {MODULE_LABELS[rec.module]} · {rec.difficulty}
            </AppText>
          </View>
          <Icon name="arrow-right" size={20} color="primary" />
        </View>
        <AppText variant="bodySm" color="textSecondary" style={styles.recAction}>
          {rec.action}
        </AppText>
        <ProgressBar
          progress={rec.severity}
          fillColor={theme.colors.highlight}
          height={5}
          style={styles.recBar}
        />
      </Card>
    </Pressable>
  );
};

const DifficultyRow: React.FC<{ item: AdaptiveDifficultyItem }> = ({ item }) => {
  const color = DIFFICULTY_COLORS[item.difficulty] ?? PALETTE.warning;
  return (
    <Card style={styles.diffCard}>
      <View style={styles.diffHead}>
        <AppText variant="bodyMd">{MODULE_LABELS[item.module]}</AppText>
        <View style={[styles.diffPill, { backgroundColor: color }]}>
          <AppText variant="labelSm" color="textInverse">
            {item.difficulty.toUpperCase()}
          </AppText>
        </View>
      </View>
      <AppText variant="labelSm" color="textMuted">
        {item.rationale}
      </AppText>
    </Card>
  );
};

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { marginVertical: SPACING.md },
  title: { marginVertical: SPACING.md },
  section: { marginTop: SPACING.md },
  sectionTitle: { marginTop: SPACING.lg, marginBottom: SPACING.xs },
  emptyBody: { marginTop: SPACING.xs },
  coachBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: RADIUS.card,
    padding: SPACING.md,
  },
  coachIcon: {
    width: 44,
    height: 44,
    borderRadius: RADIUS.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  coachMessage: { flex: 1, marginLeft: SPACING.sm },
  recCard: { marginTop: SPACING.sm },
  recHead: { flexDirection: 'row', alignItems: 'center' },
  recIcon: {
    width: 40,
    height: 40,
    borderRadius: RADIUS.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  recTitleWrap: { flex: 1, marginLeft: SPACING.sm },
  recAction: { marginTop: SPACING.sm },
  recBar: { marginTop: SPACING.sm },
  diffCard: { marginTop: SPACING.sm },
  diffHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.xxs,
  },
  diffPill: {
    paddingHorizontal: SPACING.xs,
    paddingVertical: 2,
    borderRadius: RADIUS.pill,
  },
});
