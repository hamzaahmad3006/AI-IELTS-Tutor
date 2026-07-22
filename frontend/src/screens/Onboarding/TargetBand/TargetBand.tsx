/** Onboarding — "What's your target band?" step (UI only). */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  BandSlider,
  Button,
  Card,
  Icon,
  ScreenContainer,
  useTheme,
} from '../../../components';
import { getBandColor, RADIUS, SPACING } from '../../../constants';
import { APP_CONFIG } from '../../../constants';
import { useTargetBand } from './useTargetBand';

export const TargetBand: React.FC = () => {
  const theme = useTheme();
  const {
    step,
    totalSteps,
    targetBand,
    bandUserLabel,
    recommendation,
    onChangeBand,
    onNext,
    onSkip,
  } = useTargetBand();

  const bandColor = getBandColor(targetBand);

  return (
    <ScreenContainer scroll>
      {/* Header */}
      <View style={styles.header}>
        <AppText variant="titleLg" color="primary">
          {APP_CONFIG.displayName}
        </AppText>
        <Icon name="profile" size={22} color="primary" />
      </View>

      {/* Stepper */}
      <View style={styles.stepper}>
        <View style={styles.dots}>
          {Array.from({ length: totalSteps }).map((_, index) => (
            <View
              key={index}
              style={[
                styles.dot,
                {
                  backgroundColor:
                    index < step
                      ? theme.colors.primary
                      : theme.colors.containerHighest,
                },
              ]}
            />
          ))}
        </View>
        <AppText variant="labelMd" color="textSecondary">
          Step {step} of {totalSteps}
        </AppText>
      </View>

      <Card padding={SPACING.lg} style={styles.card}>
        <AppText variant="headlineMobile" align="center">
          What's your target band?
        </AppText>
        <AppText
          variant="bodyMd"
          color="textSecondary"
          align="center"
          style={styles.subtitle}
        >
          Setting a clear goal helps our AI curate the most effective study path
          for your success.
        </AppText>

        {/* Target circle */}
        <View style={styles.circleWrap}>
          <View style={[styles.circle, { backgroundColor: bandColor }]}>
            <AppText variant="labelMd" color="textInverse">
              TARGET
            </AppText>
            <AppText variant="displayLg" color="textInverse">
              {targetBand.toFixed(1)}
            </AppText>
            <AppText variant="titleLg" color="textInverse">
              {bandUserLabel}
            </AppText>
          </View>
        </View>

        {/* Slider */}
        <View style={styles.scale}>
          <AppText variant="labelSm" color="textMuted">
            0.0
          </AppText>
          <AppText variant="labelSm" color="textMuted">
            4.5
          </AppText>
          <AppText variant="labelSm" color="textMuted">
            9.0
          </AppText>
        </View>
        <BandSlider value={targetBand} onChange={onChangeBand} />

        {/* AI recommendation */}
        <View
          style={[
            styles.recommend,
            { backgroundColor: theme.colors.cardAlt },
          ]}
        >
          <Icon name="info" size={20} color="primary" />
          <View style={styles.recommendText}>
            <AppText variant="labelMd" color="textPrimary">
              AI Recommendation
            </AppText>
            <AppText variant="bodySm" color="textSecondary" style={styles.recommendBody}>
              {recommendation}
            </AppText>
          </View>
        </View>

        <Button title="Next" icon="arrow-right" onPress={onNext} style={styles.next} />
        <Pressable onPress={onSkip} style={styles.skip}>
          <AppText variant="labelMd" color="textMuted" align="center">
            I'm not sure yet
          </AppText>
        </Pressable>
      </Card>
    </ScreenContainer>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: SPACING.md,
  },
  stepper: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.md,
  },
  dots: { flexDirection: 'row' },
  dot: { width: 34, height: 6, borderRadius: RADIUS.pill, marginRight: SPACING.xs },
  card: { marginBottom: SPACING.lg },
  subtitle: { marginTop: SPACING.sm, marginBottom: SPACING.lg },
  circleWrap: { alignItems: 'center', marginVertical: SPACING.md },
  circle: {
    width: 168,
    height: 168,
    borderRadius: 84,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scale: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: SPACING.lg,
    marginBottom: SPACING.xs,
  },
  recommend: {
    flexDirection: 'row',
    borderRadius: RADIUS.card,
    padding: SPACING.md,
    marginTop: SPACING.lg,
  },
  recommendText: { flex: 1, marginLeft: SPACING.sm },
  recommendBody: { marginTop: SPACING.xxs },
  next: { marginTop: SPACING.lg },
  skip: { marginTop: SPACING.md, paddingVertical: SPACING.xs },
});
