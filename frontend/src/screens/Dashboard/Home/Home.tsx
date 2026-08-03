/** Home dashboard (UI only). Logic in useHome. */

import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import {
  AppText,
  BandBadge,
  Card,
  Icon,
  ProgressBar,
  ScreenContainer,
  useTheme,
} from '@components';
import {
  APP_CONFIG,
  PALETTE,
  RADIUS,
  SPACING,
  type IconName,
} from '@constants';
import type { IeltsModule, ModuleProgress, ChecklistItem } from '@models';
import { useHome } from './useHome';

const MODULE_META: Record<IeltsModule, { label: string; icon: IconName }> = {
  speaking: { label: 'Speaking', icon: 'mic' },
  writing: { label: 'Writing', icon: 'writing' },
  reading: { label: 'Reading', icon: 'reading' },
  listening: { label: 'Listening', icon: 'listening' },
};

export const Home: React.FC = () => {
  const theme = useTheme();
  const { data, status, onSelectModule, onStartMockTest } = useHome();

  if (status === 'loading' || !data) {
    return (
      <ScreenContainer>
        <View style={styles.loader}>
          <ActivityIndicator color={theme.colors.primary} size="large" />
        </View>
      </ScreenContainer>
    );
  }

  const { prediction } = data;

  return (
    <ScreenContainer scroll>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View
            style={[
              styles.avatar,
              { backgroundColor: theme.colors.primaryContainer },
            ]}
          >
            <Icon name="profile" size={20} color="primary" />
          </View>
          <AppText variant="titleLg" color="primary" style={styles.brand}>
            {APP_CONFIG.displayName}
          </AppText>
        </View>
        <Icon name="bell" size={24} color="primary" />
      </View>

      {/* Greeting */}
      <AppText variant="headlineMobile">Hi, {data.greetingName}!</AppText>
      <AppText
        variant="bodyMd"
        color="textSecondary"
        style={styles.greetingSub}
      >
        Ready to push your band score higher today?
      </AppText>

      {/* Streak */}
      <View style={[styles.streak, { backgroundColor: theme.colors.card }]}>
        <Icon name="flame" size={16} color="highlight" />
        <AppText variant="labelMd" style={styles.streakText}>
          {data.streakDays} days streak
        </AppText>
      </View>

      {/* Predicted band */}
      <Card style={styles.section}>
        <AppText variant="labelMd" color="textSecondary">
          PREDICTED IELTS BAND
        </AppText>
        <View style={styles.bandRow}>
          <AppText
            variant="displayLg"
            color="primary"
            style={styles.bandNumber}
          >
            {prediction.predictedBand.toFixed(1)}
          </AppText>
          <BandBadge band={prediction.predictedBand} />
        </View>
        <AppText variant="bodyMd" color="textSecondary" style={styles.bandDesc}>
          Based on your last {prediction.basedOnSessions} practice sessions.
          You're {prediction.distanceToTarget.toFixed(1)} away from your target!
        </AppText>
        <ProgressBar
          progress={prediction.progressToTarget}
          fillColor={PALETTE.teal400}
          style={styles.bandProgress}
        />
      </Card>

      {/* Daily coach */}
      <View style={[styles.coach, { backgroundColor: PALETTE.tealContainer }]}>
        <View style={styles.coachIcon}>
          <Icon name="coach" size={22} color="onAccent" />
        </View>
        <View style={styles.coachText}>
          <AppText variant="labelMd">{data.coach.title}</AppText>
          <AppText variant="bodyMd" style={styles.coachMsg}>
            "{data.coach.message}"
          </AppText>
        </View>
      </View>

      {/* Module tiles */}
      <View style={styles.grid}>
        {data.modules.map(module => (
          <ModuleTile
            key={module.module}
            module={module}
            onPress={() => onSelectModule(module.module)}
          />
        ))}
      </View>

      {/* Checklist */}
      <Card backgroundToken="cardAlt" style={styles.section}>
        <View style={styles.checklistHead}>
          <AppText variant="titleLg">Today's Checklist</AppText>
          <AppText variant="labelMd" color="primary">
            {data.checklistCompletionPct}% Complete
          </AppText>
        </View>
        {data.checklist.map(item => (
          <ChecklistRow key={item.id} item={item} />
        ))}
      </Card>

      {/* Mock test CTA */}
      <LinearGradient
        colors={[PALETTE.indigo, PALETTE.indigoTint]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.mock}
      >
        <AppText variant="headlineMd" color="textInverse">
          Ready for a Full Simulation?
        </AppText>
        <AppText variant="bodyMd" color="textInverse" style={styles.mockBody}>
          Take a timed mock test and get instant AI-powered feedback across all
          four sections.
        </AppText>
        <Pressable style={styles.mockBtn} onPress={onStartMockTest}>
          <LinearGradient
            colors={[PALETTE.teal400, PALETTE.teal600]}
            style={styles.mockBtnInner}
          >
            <AppText variant="button" color="textInverse">
              Start Mock Test
            </AppText>
            <View style={styles.mockBtnIcon}>
              <Icon name="rocket" size={20} color="textInverse" />
            </View>
          </LinearGradient>
        </Pressable>
      </LinearGradient>
    </ScreenContainer>
  );
};

const ModuleTile: React.FC<{ module: ModuleProgress; onPress: () => void }> = ({
  module,
  onPress,
}) => {
  const theme = useTheme();
  const meta = MODULE_META[module.module];
  return (
    <Pressable
      onPress={onPress}
      style={[
        styles.tile,
        {
          backgroundColor: theme.colors.card,
          borderColor: module.isActive ? theme.colors.primary : 'transparent',
          borderWidth: module.isActive ? 2 : 0,
        },
        theme.shadows.card,
      ]}
    >
      <View
        style={[
          styles.tileIcon,
          { backgroundColor: theme.colors.primaryContainer },
        ]}
      >
        <Icon name={meta.icon} size={22} color="primary" />
      </View>
      <AppText variant="titleLg" style={styles.tileLabel}>
        {meta.label}
      </AppText>
      <View style={styles.tileFooter}>
        <AppText variant="bodySm" color="textSecondary">
          Level {module.currentLevel.toFixed(1)}
        </AppText>
        <View style={[styles.tileArrow, { borderColor: theme.colors.border }]}>
          <Icon name="arrow-right" size={16} color="primary" />
        </View>
      </View>
    </Pressable>
  );
};

const ChecklistRow: React.FC<{ item: ChecklistItem }> = ({ item }) => {
  const theme = useTheme();
  return (
    <View style={[styles.checkRow, { backgroundColor: theme.colors.card }]}>
      <View
        style={[
          styles.checkbox,
          {
            backgroundColor: item.isCompleted
              ? theme.colors.accent
              : 'transparent',
            borderColor: item.isCompleted
              ? theme.colors.accent
              : theme.colors.outlineVariant,
          },
        ]}
      >
        {item.isCompleted ? (
          <Icon name="check" size={14} color="onAccent" />
        ) : null}
      </View>
      <View style={styles.checkText}>
        <AppText
          variant="bodyMd"
          style={item.isCompleted ? styles.strike : undefined}
        >
          {item.title}
        </AppText>
        <AppText
          variant="labelSm"
          color={item.priority === 'high' ? 'primary' : 'textMuted'}
        >
          {item.subtitle}
        </AppText>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  loader: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: SPACING.md,
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center' },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  brand: { marginLeft: SPACING.xs },
  greetingSub: { marginTop: SPACING.xxs },
  streak: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xs,
    borderRadius: RADIUS.pill,
    marginTop: SPACING.md,
  },
  streakText: { marginLeft: SPACING.xs },
  section: { marginTop: SPACING.lg },
  bandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: SPACING.xs,
  },
  bandNumber: { fontSize: 56, lineHeight: 60, marginRight: SPACING.sm },
  bandDesc: { marginTop: SPACING.xs },
  bandProgress: { marginTop: SPACING.md },
  coach: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: RADIUS.card,
    padding: SPACING.md,
    marginTop: SPACING.lg,
  },
  coachIcon: {
    width: 44,
    height: 44,
    borderRadius: RADIUS.md,
    backgroundColor: PALETTE.teal,
    alignItems: 'center',
    justifyContent: 'center',
  },
  coachText: { flex: 1, marginLeft: SPACING.sm },
  coachMsg: { marginTop: 2 },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginTop: SPACING.lg,
  },
  tile: {
    width: '48%',
    borderRadius: RADIUS.card,
    padding: SPACING.md,
    marginBottom: SPACING.md,
  },
  tileIcon: {
    width: 44,
    height: 44,
    borderRadius: RADIUS.md,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: SPACING.sm,
  },
  tileLabel: { marginBottom: SPACING.sm },
  tileFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  tileArrow: {
    width: 30,
    height: 30,
    borderRadius: 15,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checklistHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.md,
  },
  checkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: RADIUS.md,
    padding: SPACING.sm,
    marginBottom: SPACING.xs,
  },
  checkbox: {
    width: 26,
    height: 26,
    borderRadius: RADIUS.sm,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkText: { flex: 1, marginLeft: SPACING.sm },
  strike: { textDecorationLine: 'line-through' },
  mock: {
    borderRadius: RADIUS.lg,
    padding: SPACING.lg,
    marginTop: SPACING.lg,
  },
  mockBody: { marginTop: SPACING.xs, opacity: 0.9 },
  mockBtn: { marginTop: SPACING.lg, alignSelf: 'flex-start' },
  mockBtnInner: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.sm,
    borderRadius: RADIUS.pill,
  },
  mockBtnIcon: { marginLeft: SPACING.xs },
});
