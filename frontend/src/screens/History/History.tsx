/** Attempt history screen (UI only). Logic in useHistory. */

import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  BandBadge,
  Button,
  Card,
  LineChart,
  Icon,
  ScreenContainer,
  useTheme,
} from '../../components';
import { getBandColor, RADIUS, SPACING } from '../../constants';
import type { IeltsModule } from '../../types';
import { useHistory, type HistoryRow } from './useHistory';

const MODULES: Array<{ value: IeltsModule; label: string }> = [
  { value: 'writing', label: 'Writing' },
  { value: 'speaking', label: 'Speaking' },
  { value: 'reading', label: 'Reading' },
  { value: 'listening', label: 'Listening' },
];

const formatDate = (iso: string): string => {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
};

export const History: React.FC = () => {
  const theme = useTheme();
  const {
    module,
    rows,
    isLoading,
    isLoadingMore,
    hasMore,
    error,
    setModule,
    trendBands,
    loadMore,
    onBack,
  } = useHistory();

  return (
    <ScreenContainer scroll>
      <View style={styles.header}>
        <Pressable onPress={onBack} hitSlop={8}>
          <Icon name="back" size={24} color="primary" />
        </Pressable>
        <AppText variant="titleLg" color="primary">
          History
        </AppText>
        <View style={styles.headerSpacer} />
      </View>

      {/* Module switcher */}
      <View style={styles.tabs}>
        {MODULES.map((item) => {
          const selected = module === item.value;
          return (
            <Pressable
              key={item.value}
              onPress={() => setModule(item.value)}
              style={[
                styles.tab,
                {
                  backgroundColor: selected
                    ? theme.colors.primary
                    : theme.colors.card,
                  borderColor: selected
                    ? theme.colors.primary
                    : theme.colors.border,
                },
              ]}
            >
              <AppText
                variant="labelMd"
                color={selected ? 'textInverse' : 'textPrimary'}
              >
                {item.label}
              </AppText>
            </Pressable>
          );
        })}
      </View>

      {trendBands.length > 0 ? (
        <Card style={styles.section} testID="history-trend">
          <AppText variant="labelMd" color="textSecondary">
            BAND TREND
          </AppText>
          <LineChart
            series={[
              {
                label:
                  MODULES.find((m) => m.value === module)?.label ?? module,
                color: theme.colors.primary,
                values: trendBands,
              },
            ]}
            height={140}
            showLegend={false}
            testID="history-trend-chart"
          />
        </Card>
      ) : null}

      {isLoading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      ) : error ? (
        <Card style={styles.section} backgroundToken="cardAlt">
          <AppText variant="bodyMd" color="error">
            {error}
          </AppText>
        </Card>
      ) : rows.length === 0 ? (
        <Card style={styles.section} backgroundToken="cardAlt">
          <AppText variant="titleLg">No attempts yet</AppText>
          <AppText variant="bodyMd" color="textSecondary" style={styles.emptyBody}>
            Complete a {module} practice session and it will appear here with your
            band and score.
          </AppText>
        </Card>
      ) : (
        <>
          {rows.map((row) => (
            <HistoryCard key={row.attemptId} row={row} />
          ))}
          {hasMore ? (
            <Button
              title={isLoadingMore ? 'Loading…' : 'Load more'}
              variant="secondary"
              onPress={loadMore}
              loading={isLoadingMore}
              style={styles.section}
            />
          ) : null}
        </>
      )}
    </ScreenContainer>
  );
};

const HistoryCard: React.FC<{ row: HistoryRow }> = ({ row }) => {
  const band = row.band;
  return (
    <Card style={styles.card}>
      <View style={styles.cardRow}>
        <View style={styles.cardText}>
          <AppText variant="titleLg">{row.detail}</AppText>
          <AppText variant="labelSm" color="textMuted" style={styles.cardMeta}>
            {formatDate(row.createdAt)}
            {row.status && row.status !== 'scored' ? ` · ${row.status}` : ''}
          </AppText>
        </View>
        {band !== null ? (
          <View style={styles.bandWrap}>
            <AppText variant="headlineMd" style={{ color: getBandColor(band) }}>
              {band.toFixed(1)}
            </AppText>
            <BandBadge band={band} />
          </View>
        ) : (
          <AppText variant="labelMd" color="textMuted">
            —
          </AppText>
        )}
      </View>
    </Card>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: SPACING.md,
  },
  headerSpacer: { width: 24 },
  center: { paddingVertical: SPACING.xxl, alignItems: 'center' },
  tabs: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: SPACING.sm },
  tab: {
    borderWidth: 1,
    borderRadius: RADIUS.pill,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.xs,
    marginRight: SPACING.xs,
    marginBottom: SPACING.xs,
  },
  section: { marginTop: SPACING.md },
  emptyBody: { marginTop: SPACING.xs },
  card: { marginBottom: SPACING.sm },
  cardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  cardText: { flex: 1 },
  cardMeta: { marginTop: SPACING.xxs },
  bandWrap: { alignItems: 'flex-end' },
});
