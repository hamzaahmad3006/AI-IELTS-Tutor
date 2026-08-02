/** Writing feedback (UI only). Logic in useFeedback. */

import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  Button,
  Card,
  DiffText,
  diffWords,
  summariseDiff,
  Icon,
  ProgressBar,
  ScreenContainer,
  useTheme,
} from '../../../components';
import {
  getBandColor,
  PALETTE,
  RADIUS,
  SPACING,
  type IconName,
} from '../../../constants';
import type {
  EssaySegment,
  FeedbackTab,
  KeyImprovement,
  WritingFeedback,
} from '../../../types';
import { useFeedback } from './useFeedback';

const CRITERIA_LABELS: Array<{ key: keyof WritingFeedback['criteria']; label: string }> = [
  { key: 'taskResponse', label: 'Task Response' },
  { key: 'coherenceCohesion', label: 'Cohesion & Coherence' },
  { key: 'lexicalResource', label: 'Lexical Resource' },
  { key: 'grammaticalRange', label: 'Grammatical Range' },
];

export const Feedback: React.FC = () => {
  const theme = useTheme();
  const { feedback, isLoading, activeTab, setTab, onExport, onBack } =
    useFeedback();

  if (isLoading || !feedback) {
    return (
      <ScreenContainer>
        <View style={styles.loader}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      </ScreenContainer>
    );
  }

  const overallColor = getBandColor(feedback.overallBand);

  return (
    <ScreenContainer scroll>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={onBack} hitSlop={8}>
          <Icon name="back" size={24} color="primary" />
        </Pressable>
        <AppText variant="titleLg" color="primary">
          Writing Feedback
        </AppText>
        <Icon name="bell" size={22} color="primary" />
      </View>

      <AppText variant="labelSm" color="textMuted">
        Practice · {feedback.taskLabel}
      </AppText>
      <AppText variant="headlineMobile" style={styles.title}>
        {feedback.title}
      </AppText>
      <AppText variant="bodySm" color="textSecondary" style={styles.summary}>
        {feedback.analysisSummary}
      </AppText>

      {/* Overall band */}
      <Card style={styles.section}>
        <View style={styles.overallRow}>
          <View style={styles.overallText}>
            <AppText variant="labelMd" color="textSecondary">
              Overall Band
            </AppText>
            <AppText variant="titleLg">{feedback.bandLabel}</AppText>
          </View>
          <View style={[styles.bandRing, { borderColor: overallColor }]}>
            <AppText variant="headlineMd" style={{ color: overallColor }}>
              {feedback.overallBand.toFixed(1)}
            </AppText>
          </View>
        </View>
      </Card>

      {/* Criteria score */}
      <Card style={styles.section}>
        <View style={styles.criteriaHead}>
          <Icon name="progress" size={18} color="primary" />
          <AppText variant="titleLg" style={styles.criteriaTitle}>
            Criteria Score
          </AppText>
        </View>
        {CRITERIA_LABELS.map(({ key, label }) => {
          const band = feedback.criteria[key];
          const color = getBandColor(band);
          return (
            <View key={key} style={styles.criteriaRow}>
              <View style={styles.criteriaLabelRow}>
                <AppText variant="bodyMd">{label}</AppText>
                <AppText variant="labelMd" style={{ color }}>
                  {band.toFixed(1)}
                </AppText>
              </View>
              <ProgressBar progress={band / 9} fillColor={color} height={6} />
            </View>
          );
        })}
      </Card>

      {/* Master tip */}
      <View style={[styles.tip, { backgroundColor: PALETTE.tealContainer }]}>
        <AppText variant="labelMd" style={styles.tipTitle}>
          Master Tip
        </AppText>
        <AppText variant="bodyMd" style={styles.tipBody}>
          {feedback.masterTip}
        </AppText>
        <View style={styles.tipLink}>
          <AppText variant="labelMd" style={styles.tipLinkText}>
            Learn more
          </AppText>
          <Icon name="arrow-right" size={16} color="accent" />
        </View>
      </View>

      {/* Draft / Model tabs */}
      <Card style={styles.section}>
        <View style={styles.tabs}>
          <TabButton
            label="Your Draft"
            tab="draft"
            activeTab={activeTab}
            onPress={setTab}
          />
          <TabButton
            label="Model Essay"
            tab="model"
            activeTab={activeTab}
            onPress={setTab}
          />
          <TabButton
            label="Changes"
            tab="changes"
            activeTab={activeTab}
            onPress={setTab}
          />
        </View>

        {activeTab === 'draft' ? (
          <>
            <View style={styles.legend}>
              <LegendDot color={theme.colors.error} label="Error" />
              <LegendDot color={theme.colors.accent} label="Suggestion" />
            </View>
            <AppText variant="bodyLg" style={styles.essay}>
              {feedback.draftSegments.map((segment, index) => (
                <Segment key={index} segment={segment} />
              ))}
            </AppText>
          </>
        ) : activeTab === 'model' ? (
          <AppText variant="bodyLg" style={styles.essay}>
            {feedback.modelEssay}
          </AppText>
        ) : (
          <ChangesTab
            draft={feedback.draftSegments.map((segment) => segment.text).join('')}
            model={feedback.modelEssay}
          />
        )}

        <View style={styles.essayFooter}>
          <AppText variant="labelSm" color="textMuted">
            Word Count: {feedback.wordCount} words
          </AppText>
          <Button
            title="Export PDF"
            icon="export"
            fullWidth={false}
            onPress={onExport}
            style={styles.exportBtn}
          />
        </View>
      </Card>

      {/* Key improvements */}
      <AppText variant="headlineMd" style={styles.section}>
        Key Improvements
      </AppText>
      {feedback.improvements.map((improvement) => (
        <ImprovementCard key={improvement.id} improvement={improvement} />
      ))}
    </ScreenContainer>
  );
};

const TabButton: React.FC<{
  label: string;
  tab: FeedbackTab;
  activeTab: FeedbackTab;
  onPress: (tab: FeedbackTab) => void;
}> = ({ label, tab, activeTab, onPress }) => {
  const theme = useTheme();
  const isActive = tab === activeTab;
  return (
    <Pressable
      onPress={() => onPress(tab)}
      style={[
        styles.tab,
        {
          backgroundColor: isActive ? theme.colors.card : 'transparent',
        },
        isActive ? theme.shadows.card : null,
      ]}
    >
      <AppText variant="labelMd" color={isActive ? 'primary' : 'textMuted'}>
        {label}
      </AppText>
    </Pressable>
  );
};

const ChangesTab: React.FC<{ draft: string; model: string }> = ({
  draft,
  model,
}) => {
  // Diffing is O(n*m) in words, so it is memoised against the two texts rather
  // than recomputed on every tab switch or re-render.
  const tokens = React.useMemo(() => diffWords(draft, model), [draft, model]);
  const summary = React.useMemo(() => summariseDiff(tokens), [tokens]);

  return (
    <View testID="changes-tab">
      <AppText variant="labelSm" color="textMuted" style={styles.diffSummary}>
        {`${summary.added} added · ${summary.removed} removed · ${summary.unchanged} kept`}
      </AppText>
      <DiffText tokens={tokens} testID="essay-diff" />
    </View>
  );
};

const LegendDot: React.FC<{ color: string; label: string }> = ({
  color,
  label,
}) => (
  <View style={styles.legendItem}>
    <View style={[styles.dot, { backgroundColor: color }]} />
    <AppText variant="labelSm" color="textSecondary">
      {label}
    </AppText>
  </View>
);

const Segment: React.FC<{ segment: EssaySegment }> = ({ segment }) => {
  const theme = useTheme();
  if (segment.kind === 'error') {
    return (
      <AppText
        variant="bodyLg"
        style={{
          backgroundColor: theme.colors.errorHighlight,
          textDecorationLine: 'underline',
        }}
      >
        {segment.text}
      </AppText>
    );
  }
  if (segment.kind === 'suggestion') {
    return (
      <AppText variant="bodyLg" style={{ backgroundColor: PALETTE.tealContainer }}>
        {segment.text}
      </AppText>
    );
  }
  return <AppText variant="bodyLg">{segment.text}</AppText>;
};

const ImprovementCard: React.FC<{ improvement: KeyImprovement }> = ({
  improvement,
}) => {
  const theme = useTheme();
  return (
    <Card style={styles.improvement}>
      <View style={styles.improvementRow}>
        <View style={[styles.improvementIcon, { backgroundColor: theme.colors.cardAlt }]}>
          <Icon name={improvement.icon as IconName} size={20} color="primary" />
        </View>
        <View style={styles.improvementText}>
          <AppText variant="titleLg">{improvement.title}</AppText>
          <AppText variant="bodySm" color="textSecondary" style={styles.improvementDesc}>
            {improvement.description}
          </AppText>
        </View>
      </View>
    </Card>
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
  title: { marginTop: SPACING.xxs },
  summary: { marginTop: SPACING.xs },
  section: { marginTop: SPACING.lg },
  overallRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  overallText: { flex: 1 },
  bandRing: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  criteriaHead: { flexDirection: 'row', alignItems: 'center', marginBottom: SPACING.md },
  criteriaTitle: { marginLeft: SPACING.xs },
  criteriaRow: { marginBottom: SPACING.md },
  criteriaLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.xs,
  },
  tip: {
    borderRadius: RADIUS.card,
    padding: SPACING.md,
    marginTop: SPACING.lg,
  },
  tipTitle: { color: PALETTE.tealDeep },
  tipBody: { marginTop: SPACING.xxs, color: PALETTE.ink2 },
  tipLink: { flexDirection: 'row', alignItems: 'center', marginTop: SPACING.sm },
  tipLinkText: { color: PALETTE.teal, marginRight: SPACING.xxs },
  tabs: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0,0,0,0.04)',
    borderRadius: RADIUS.pill,
    padding: SPACING.xxs,
    marginBottom: SPACING.md,
  },
  tab: {
    flex: 1,
    paddingVertical: SPACING.xs,
    borderRadius: RADIUS.pill,
    alignItems: 'center',
  },
  legend: { flexDirection: 'row', marginBottom: SPACING.sm },
  legendItem: { flexDirection: 'row', alignItems: 'center', marginRight: SPACING.md },
  dot: { width: 8, height: 8, borderRadius: 4, marginRight: SPACING.xxs },
  essay: { marginTop: SPACING.xs },
  diffSummary: { marginBottom: SPACING.sm },
  essayFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: SPACING.md,
  },
  exportBtn: { paddingHorizontal: SPACING.md },
  improvement: { marginTop: SPACING.md },
  improvementRow: { flexDirection: 'row' },
  improvementIcon: {
    width: 44,
    height: 44,
    borderRadius: RADIUS.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  improvementText: { flex: 1, marginLeft: SPACING.sm },
  improvementDesc: { marginTop: SPACING.xxs },
});
