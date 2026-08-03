/** Full mock test (UI only). Logic in useMockTest. */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  BandBadge,
  Button,
  Card,
  Icon,
  Input,
  ScreenContainer,
  TimerBar,
  useTheme,
} from '@components';
import { getBandColor, RADIUS, SPACING } from '@constants';
import type { MockResult, ReadinessReport } from '@models';
import { useMockTest } from './useMockTest';

const MODULE_LABELS: Record<string, string> = {
  listening: 'Listening',
  reading: 'Reading',
  writing: 'Writing',
  speaking: 'Speaking',
};

export const MockTest: React.FC = () => {
  const theme = useTheme();
  const {
    stage,
    test,
    isStarting,
    isSubmitting,
    error,
    sectionIndex,
    isLastSection,
    writingText,
    speakingText,
    setWritingText,
    setSpeakingText,
    secondsLeft,
    timerState,
    isWarning,
    startTimer,
    pauseTimer,
    resetTimer,
    start,
    nextSection,
    result,
    onBack,
  } = useMockTest();

  if (stage === 'result' && result) {
    return <ReportView result={result} onBack={onBack} />;
  }

  if (stage === 'intro' || !test) {
    return (
      <ScreenContainer scroll>
        <Header title="Full mock test" onBack={onBack} />
        <Card style={styles.section} testID="mock-intro">
          <AppText variant="titleLg">Sit all four sections</AppText>
          <AppText variant="bodySm" color="textSecondary" style={styles.body}>
            Listening, Reading, Writing and Speaking, each with its real time
            allowance. You can skip a section — the report will say so rather
            than scoring it as zero.
          </AppText>
        </Card>
        {error ? (
          <AppText variant="labelMd" color="error" style={styles.section}>
            {error}
          </AppText>
        ) : null}
        <Button
          title={isStarting ? 'Preparing…' : 'Start mock test'}
          onPress={start}
          disabled={isStarting}
          style={styles.section}
          testID="mock-start"
        />
      </ScreenContainer>
    );
  }

  const section = test.sections[sectionIndex];

  return (
    <ScreenContainer scroll>
      <Header
        title={`Section ${sectionIndex + 1} of ${test.sections.length}`}
        onBack={onBack}
      />

      <View style={styles.sectionChips}>
        {test.sections.map((s, index) => (
          <View
            key={s.module}
            style={[
              styles.chip,
              {
                backgroundColor:
                  index === sectionIndex
                    ? theme.colors.primary
                    : theme.colors.containerHighest,
              },
            ]}
          >
            <AppText
              variant="labelSm"
              color={index === sectionIndex ? 'textInverse' : 'textSecondary'}
            >
              {MODULE_LABELS[s.module]}
            </AppText>
          </View>
        ))}
      </View>

      <TimerBar
        secondsLeft={secondsLeft}
        state={timerState}
        isWarning={isWarning}
        onStart={startTimer}
        onPause={pauseTimer}
        onReset={resetTimer}
        testID="mock-timer"
        expiredNote="Time is up for this section. Your answers are kept."
      />

      <Card style={styles.section} testID={`mock-section-${section.module}`}>
        <AppText variant="labelMd" color="textSecondary">
          {MODULE_LABELS[section.module].toUpperCase()}
        </AppText>
        {section.module === 'writing' ? (
          <Input
            label=""
            value={writingText}
            onChangeText={setWritingText}
            placeholder="Write your Task 2 response…"
            multiline
            autoCapitalize="sentences"
            testID="mock-writing"
          />
        ) : section.module === 'speaking' ? (
          <Input
            label=""
            value={speakingText}
            onChangeText={setSpeakingText}
            placeholder="Type what you would say…"
            multiline
            autoCapitalize="sentences"
            testID="mock-speaking"
          />
        ) : (
          // The objective sections are sat in their own practice runners; this
          // states that plainly rather than half-rendering a question list.
          <AppText variant="bodySm" color="textSecondary" style={styles.body}>
            {`Open ${
              MODULE_LABELS[section.module]
            } practice to answer this section, or skip it — the report will say it was not attempted.`}
          </AppText>
        )}
      </Card>

      {error ? (
        <AppText variant="labelMd" color="error" style={styles.section}>
          {error}
        </AppText>
      ) : null}

      <Button
        title={
          isLastSection
            ? isSubmitting
              ? 'Scoring…'
              : 'Finish and see report'
            : 'Next section'
        }
        onPress={nextSection}
        disabled={isSubmitting}
        style={styles.section}
        testID="mock-next"
      />
    </ScreenContainer>
  );
};

const ReportView: React.FC<{ result: MockResult; onBack: () => void }> = ({
  result,
  onBack,
}) => {
  const report: ReadinessReport = result.readiness;
  return (
    <ScreenContainer scroll>
      <Header title="Readiness report" onBack={onBack} />

      <Card style={styles.section} testID="mock-report">
        <AppText variant="labelMd" color="textSecondary">
          {report.verdict.toUpperCase()}
        </AppText>
        <View style={styles.overallRow}>
          <AppText
            variant="displayLg"
            style={{ color: getBandColor(report.overallBand ?? 0) }}
          >
            {report.overallBand !== null ? report.overallBand.toFixed(1) : '—'}
          </AppText>
          {report.overallBand !== null ? (
            <BandBadge band={report.overallBand} />
          ) : null}
        </View>
        <AppText variant="bodyMd" color="textSecondary">
          {report.headline}
        </AppText>
      </Card>

      <Card style={styles.section}>
        <AppText variant="labelMd" color="textSecondary">
          BY SECTION
        </AppText>
        {report.modules.map(module => (
          <View key={module.module} style={styles.moduleRow}>
            <View style={styles.grow}>
              <AppText variant="bodyMd">
                {MODULE_LABELS[module.module] ?? module.module}
              </AppText>
              <AppText variant="labelSm" color="textMuted">
                {module.verdict}
              </AppText>
            </View>
            <AppText
              variant="labelMd"
              style={
                module.band !== null
                  ? { color: getBandColor(module.band) }
                  : undefined
              }
              color={module.band === null ? 'textMuted' : undefined}
            >
              {module.band !== null ? module.band.toFixed(1) : 'Not sat'}
            </AppText>
          </View>
        ))}
      </Card>

      <Card style={styles.section} backgroundToken="cardAlt">
        <AppText variant="labelMd" color="textSecondary">
          WHAT TO DO NEXT
        </AppText>
        <AppText variant="bodyMd" style={styles.body}>
          {report.advice}
        </AppText>
      </Card>

      <Button title="Done" onPress={onBack} style={styles.section} />
    </ScreenContainer>
  );
};

const Header: React.FC<{ title: string; onBack: () => void }> = ({
  title,
  onBack,
}) => (
  <View style={styles.header}>
    <Pressable
      onPress={onBack}
      accessibilityRole="button"
      accessibilityLabel="Back"
    >
      <Icon name="back" size={22} color="primary" />
    </Pressable>
    <AppText variant="titleLg" style={styles.grow}>
      {title}
    </AppText>
  </View>
);

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    marginBottom: SPACING.md,
  },
  grow: { flex: 1 },
  section: { marginTop: SPACING.md },
  body: { marginTop: SPACING.xs },
  sectionChips: { flexDirection: 'row', flexWrap: 'wrap', gap: SPACING.sm },
  chip: {
    borderRadius: RADIUS.pill,
    paddingVertical: 4,
    paddingHorizontal: SPACING.sm,
  },
  overallRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginVertical: SPACING.sm,
  },
  moduleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    marginTop: SPACING.sm,
  },
});
