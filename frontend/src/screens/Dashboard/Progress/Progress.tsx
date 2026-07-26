/** Progress & analytics screen (UI only). Logic in useProgress. */

import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import {
  AppText,
  BandBadge,
  Button,
  Card,
  Icon,
  ProgressBar,
  ScreenContainer,
  useTheme,
} from '../../../components';
import { getBandColor, RADIUS, SPACING } from '../../../constants';
import type {
  ModuleProgressStat,
  PredictionResponse,
  WeaknessItem,
} from '../../../types';
import { useProgress } from './useProgress';

const MODULE_LABELS: Record<string, string> = {
  speaking: 'Speaking',
  writing: 'Writing',
  reading: 'Reading',
  listening: 'Listening',
};

const prettyTag = (tag: string): string =>
  tag.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export const Progress: React.FC = () => {
  const theme = useTheme();
  const {
    progress,
    prediction,
    weaknesses,
    isLoading,
    error,
    reload,
    openHistory,
  } = useProgress();

  if (isLoading) {
    return (
      <ScreenContainer>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      </ScreenContainer>
    );
  }

  if (error || !progress) {
    return (
      <ScreenContainer>
        <View style={styles.center}>
          <Icon name="info" size={40} color="error" />
          <AppText variant="bodyMd" color="textSecondary" align="center" style={styles.errorText}>
            {error ?? 'No progress data yet.'}
          </AppText>
          <Button title="Retry" onPress={reload} fullWidth={false} />
        </View>
      </ScreenContainer>
    );
  }

  const hasAttempts = progress.totalAttempts > 0;

  return (
    <ScreenContainer scroll>
      <AppText variant="headlineMobile" style={styles.title}>
        Your Progress
      </AppText>

      {!hasAttempts ? (
        <Card style={styles.section} backgroundToken="cardAlt">
          <AppText variant="titleLg">No practice yet</AppText>
          <AppText variant="bodyMd" color="textSecondary" style={styles.emptyBody}>
            Complete a practice session in any module and your bands, trends and
            predicted score will appear here.
          </AppText>
        </Card>
      ) : null}

      {/* Overall */}
      <Card style={styles.section}>
        <View style={styles.overallRow}>
          <View>
            <AppText variant="labelMd" color="textSecondary">
              CURRENT OVERALL
            </AppText>
            <AppText
              variant="displayLg"
              style={{ color: getBandColor(progress.overallBand ?? 0) }}
            >
              {progress.overallBand !== null ? progress.overallBand.toFixed(1) : '—'}
            </AppText>
            <AppText variant="bodySm" color="textMuted">
              {progress.totalAttempts} practice{progress.totalAttempts === 1 ? '' : 's'}
            </AppText>
          </View>
          {progress.overallBand !== null ? (
            <BandBadge band={progress.overallBand} />
          ) : null}
        </View>
      </Card>

      {/* Prediction */}
      {prediction ? <PredictionCard prediction={prediction} /> : null}

      {/* Per-module */}
      <AppText variant="titleLg" style={styles.sectionTitle}>
        By module
      </AppText>
      {progress.modules.map((module) => (
        <ModuleRow key={module.module} stat={module} />
      ))}

      <Button
        title="View attempt history"
        variant="secondary"
        icon="arrow-right"
        onPress={openHistory}
        style={styles.section}
      />

      {/* Weaknesses */}
      {weaknesses.length > 0 ? (
        <>
          <AppText variant="titleLg" style={styles.sectionTitle}>
            Focus areas
          </AppText>
          {weaknesses.slice(0, 5).map((weakness) => (
            <WeaknessRow key={`${weakness.module}-${weakness.tag}`} weakness={weakness} />
          ))}
        </>
      ) : null}
    </ScreenContainer>
  );
};

const PredictionCard: React.FC<{ prediction: PredictionResponse }> = ({
  prediction,
}) => {
  const theme = useTheme();
  const predicted = prediction.predictedOverall;
  return (
    <Card style={styles.section} backgroundToken="cardAlt">
      <View style={styles.predictionHead}>
        <Icon name="sparkle" size={18} color="primary" />
        <AppText variant="labelMd" color="primary" style={styles.predictionLabel}>
          PREDICTED BAND
        </AppText>
      </View>
      <View style={styles.predictionRow}>
        <AppText
          variant="headlineLg"
          style={{ color: getBandColor(predicted ?? 0) }}
        >
          {predicted !== null ? predicted.toFixed(1) : '—'}
        </AppText>
        <View style={styles.confidenceWrap}>
          <AppText variant="labelSm" color="textSecondary">
            Confidence {Math.round(prediction.confidence * 100)}%
          </AppText>
          <ProgressBar
            progress={prediction.confidence}
            height={5}
            fillColor={theme.colors.primary}
            style={styles.confidenceBar}
          />
        </View>
      </View>
      {prediction.horizonDate ? (
        <AppText variant="bodySm" color="textSecondary" style={styles.horizon}>
          Projected for your exam on {prediction.horizonDate}
        </AppText>
      ) : null}
      <AppText variant="labelSm" color="textMuted" style={styles.disclaimer}>
        {prediction.note}
      </AppText>
    </Card>
  );
};

const ModuleRow: React.FC<{ stat: ModuleProgressStat }> = ({ stat }) => {
  const band = stat.currentBand;
  const color = getBandColor(band ?? 0);
  return (
    <Card style={styles.moduleCard}>
      <View style={styles.moduleHead}>
        <AppText variant="bodyMd">{MODULE_LABELS[stat.module] ?? stat.module}</AppText>
        <AppText variant="labelMd" style={{ color }}>
          {band !== null ? band.toFixed(1) : '—'}
        </AppText>
      </View>
      <ProgressBar progress={(band ?? 0) / 9} fillColor={color} height={6} />
      <AppText variant="labelSm" color="textMuted" style={styles.moduleMeta}>
        {stat.attempts} attempt{stat.attempts === 1 ? '' : 's'}
        {stat.averageBand !== null ? ` · avg ${stat.averageBand.toFixed(1)}` : ''}
      </AppText>
    </Card>
  );
};

const WeaknessRow: React.FC<{ weakness: WeaknessItem }> = ({ weakness }) => {
  const theme = useTheme();
  return (
    <Card style={styles.moduleCard}>
      <View style={styles.moduleHead}>
        <AppText variant="bodyMd">{prettyTag(weakness.tag)}</AppText>
        <View style={[styles.modulePill, { backgroundColor: theme.colors.primaryContainer }]}>
          <AppText variant="labelSm" color="primary">
            {MODULE_LABELS[weakness.module] ?? weakness.module}
          </AppText>
        </View>
      </View>
      <ProgressBar
        progress={weakness.severity}
        fillColor={theme.colors.highlight}
        height={5}
      />
      <AppText variant="labelSm" color="textMuted" style={styles.moduleMeta}>
        Seen {weakness.occurrences} time{weakness.occurrences === 1 ? '' : 's'}
      </AppText>
    </Card>
  );
};

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { marginVertical: SPACING.md },
  title: { marginVertical: SPACING.md },
  section: { marginTop: SPACING.md },
  sectionTitle: { marginTop: SPACING.lg },
  emptyBody: { marginTop: SPACING.xs },
  overallRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  predictionHead: { flexDirection: 'row', alignItems: 'center' },
  predictionLabel: { marginLeft: SPACING.xxs },
  predictionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: SPACING.xs,
  },
  confidenceWrap: { flex: 1, marginLeft: SPACING.lg },
  confidenceBar: { marginTop: SPACING.xxs },
  horizon: { marginTop: SPACING.xs },
  disclaimer: { marginTop: SPACING.xs },
  moduleCard: { marginTop: SPACING.sm },
  moduleHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.xs,
  },
  modulePill: {
    paddingHorizontal: SPACING.xs,
    paddingVertical: 2,
    borderRadius: RADIUS.pill,
  },
  moduleMeta: { marginTop: SPACING.xxs },
});
