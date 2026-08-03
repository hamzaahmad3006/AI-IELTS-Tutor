/** Progress & analytics screen (UI only). Logic in useProgress. */

import React from 'react';
import { StyleSheet, View } from 'react-native';
import {
  AppText,
  BandBadge,
  Button,
  Card,
  EmptyState,
  Icon,
  LineChart,
  SkeletonCard,
  ProgressBar,
  RadarChart,
  ScreenContainer,
  useTheme,
  type LineSeries,
  type RadarAxis,
} from '../../../components';
import { getBandColor, RADIUS, SPACING } from '../../../constants';
import type {
  ConsistencyStats,
  InsightsResponse,
  ModuleProgressStat,
  PredictionModules,
  PredictionResponse,
  TrendResponse,
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
  const {
    progress,
    prediction,
    trend,
    insights,
    weaknesses,
    isLoading,
    error,
    reload,
    openHistory,
    openPlan,
  } = useProgress();

  if (isLoading) {
    // Skeletons rather than a spinner: the screen's shape is known, so this
    // shows what is coming and the layout does not jump when data lands.
    return (
      <ScreenContainer scroll>
        <AppText variant="headlineMobile" style={styles.title}>
          Your Progress
        </AppText>
        <SkeletonCard lines={2} />
        <SkeletonCard lines={4} />
        <SkeletonCard lines={3} />
      </ScreenContainer>
    );
  }

  if (error || !progress) {
    return (
      <ScreenContainer>
        <EmptyState
          variant="error"
          title="Could not load your progress"
          message={error ?? 'No progress data yet.'}
          actionLabel="Retry"
          onAction={reload}
        />
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

      {/* Band trend + module balance */}
      {trend ? <TrendCard trend={trend} /> : null}
      <BalanceCard modules={progress.modules} />

      {/* Insights + consistency */}
      {insights ? <InsightsCard insights={insights} /> : null}
      {insights ? <ConsistencyCard stats={insights.consistency} /> : null}

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
        title="My study plan"
        variant="secondary"
        icon="arrow-right"
        onPress={openPlan}
        style={styles.section}
        testID="open-plan"
      />

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

const TrendCard: React.FC<{ trend: TrendResponse }> = ({ trend }) => {
  const theme = useTheme();

  // Overall only: four module lines on a phone-width chart is unreadable, and
  // the per-module breakdown already lives in the radar and the rows below.
  const series: LineSeries[] = [
    {
      label: 'Overall band',
      color: theme.colors.primary,
      values: trend.overall.map((point) => point.band),
    },
  ];

  return (
    <Card style={styles.section}>
      <AppText variant="labelMd" color="textSecondary">
        BAND TREND
      </AppText>
      <LineChart series={series} testID="band-trend-chart" />
    </Card>
  );
};

const BalanceCard: React.FC<{ modules: ModuleProgressStat[] }> = ({
  modules,
}) => {
  const axes: RadarAxis[] = modules.map((stat) => ({
    label: MODULE_LABELS[stat.module] ?? stat.module,
    value: stat.currentBand,
  }));

  return (
    <Card style={styles.section}>
      <AppText variant="labelMd" color="textSecondary">
        MODULE BALANCE
      </AppText>
      <View style={styles.radarWrap}>
        <RadarChart axes={axes} testID="module-balance-chart" />
      </View>
    </Card>
  );
};

const InsightsCard: React.FC<{ insights: InsightsResponse }> = ({
  insights,
}) => {
  const theme = useTheme();
  return (
    <Card style={styles.section} testID="insights-card">
      <AppText variant="labelMd" color="textSecondary">
        WHAT THIS MEANS
      </AppText>
      <AppText variant="bodyMd" style={styles.summary}>
        {insights.summary}
      </AppText>

      {insights.strengths.length > 0 ? (
        <View style={styles.insightGroup}>
          <AppText variant="labelSm" color="textMuted">
            STRENGTHS
          </AppText>
          {insights.strengths.map((s) => (
            <View key={`s-${s.module}`} style={styles.insightRow}>
              <View
                style={[styles.dot, { backgroundColor: getBandColor(s.band) }]}
              />
              <AppText variant="bodySm" style={styles.insightText}>
                {`${s.label} — band ${s.band.toFixed(1)}, ${s.detail}`}
              </AppText>
            </View>
          ))}
        </View>
      ) : null}

      {insights.weaknesses.length > 0 ? (
        <View style={styles.insightGroup}>
          <AppText variant="labelSm" color="textMuted">
            FOCUS NEXT
          </AppText>
          {insights.weaknesses.map((w) => (
            <View key={`w-${w.module}-${w.tag}`} style={styles.insightRow}>
              <View
                style={[styles.dot, { backgroundColor: theme.colors.warning }]}
              />
              <AppText variant="bodySm" style={styles.insightText}>
                {`${w.tagLabel} — ${w.detail.toLowerCase()}`}
              </AppText>
            </View>
          ))}
        </View>
      ) : null}
    </Card>
  );
};

const ConsistencyCard: React.FC<{ stats: ConsistencyStats }> = ({ stats }) => {
  const theme = useTheme();
  // Scale bars against the busiest week so a quiet history still reads.
  const peak = Math.max(1, ...stats.weeks.map((w) => w.attempts));

  return (
    <Card style={styles.section} testID="consistency-card">
      <AppText variant="labelMd" color="textSecondary">
        CONSISTENCY
      </AppText>

      <View style={styles.statRow}>
        <Stat label="Current streak" value={`${stats.currentStreak}d`} />
        <Stat label="Best streak" value={`${stats.longestStreak}d`} />
        <Stat label="Active (30d)" value={`${stats.activeDaysLast30}d`} />
      </View>

      <View style={styles.bars}>
        {stats.weeks.map((w) => (
          <View key={w.weekStart} style={styles.barSlot}>
            <View
              style={[
                styles.bar,
                {
                  // Zero weeks keep a hairline so the gap is visibly a gap.
                  height: Math.max(2, (w.attempts / peak) * 44),
                  backgroundColor:
                    w.attempts > 0
                      ? theme.colors.primary
                      : theme.colors.containerHighest,
                },
              ]}
            />
          </View>
        ))}
      </View>
      <AppText variant="labelSm" color="textMuted">
        Practices per week, last 8 weeks
      </AppText>

      <AppText variant="labelSm" color="textMuted" style={styles.timeNote}>
        {stats.measuredSpeakingMinutes !== null
          ? `${stats.measuredSpeakingMinutes} min spoken. ${stats.timeNote}`
          : stats.timeNote}
      </AppText>
    </Card>
  );
};

const Stat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <View style={styles.stat}>
    <AppText variant="titleLg">{value}</AppText>
    <AppText variant="labelSm" color="textMuted">
      {label}
    </AppText>
  </View>
);

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
      <VelocityRows velocity={prediction.velocityPerWeek} />

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

const VelocityRows: React.FC<{ velocity: PredictionModules }> = ({
  velocity,
}) => {
  const theme = useTheme();
  const entries = (
    Object.entries(velocity) as [keyof PredictionModules, number | null][]
  ).filter(([, value]) => value !== null && value !== 0);

  if (entries.length === 0) {
    // Velocity needs at least two scored attempts in a module to mean
    // anything; showing "0.00/wk" everywhere would look like stagnation
    // rather than absence of data.
    return (
      <AppText variant="labelSm" color="textMuted" style={styles.velocityNote}>
        Practise a module twice and your weekly rate of change appears here.
      </AppText>
    );
  }

  return (
    <View style={styles.velocityWrap} testID="velocity-rows">
      <AppText variant="labelSm" color="textMuted">
        WEEKLY CHANGE
      </AppText>
      {entries.map(([module, value]) => {
        const rate = value ?? 0;
        return (
          <View key={module} style={styles.velocityRow}>
            <AppText variant="bodySm" color="textSecondary">
              {MODULE_LABELS[module] ?? module}
            </AppText>
            <AppText
              variant="labelMd"
              style={{
                color: rate > 0 ? theme.colors.success : theme.colors.error,
              }}
            >
              {`${rate > 0 ? '+' : ''}${rate.toFixed(2)} band/wk`}
            </AppText>
          </View>
        );
      })}
    </View>
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
  velocityWrap: { marginTop: SPACING.md, gap: 2 },
  velocityRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  velocityNote: { marginTop: SPACING.md },
  confidenceWrap: { flex: 1, marginLeft: SPACING.lg },
  confidenceBar: { marginTop: SPACING.xxs },
  horizon: { marginTop: SPACING.xs },
  disclaimer: { marginTop: SPACING.xs },
  moduleCard: { marginTop: SPACING.sm },
  radarWrap: { alignItems: 'center', marginTop: SPACING.sm },
  summary: { marginTop: SPACING.xs },
  insightGroup: { marginTop: SPACING.md, gap: 4 },
  insightRow: { flexDirection: 'row', alignItems: 'center', gap: SPACING.sm },
  insightText: { flex: 1 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  statRow: { flexDirection: 'row', marginTop: SPACING.sm },
  stat: { flex: 1 },
  bars: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 6,
    height: 48,
    marginTop: SPACING.md,
    marginBottom: SPACING.xs,
  },
  barSlot: { flex: 1, justifyContent: 'flex-end' },
  bar: { width: '100%', borderRadius: RADIUS.sm },
  timeNote: { marginTop: SPACING.sm },
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
