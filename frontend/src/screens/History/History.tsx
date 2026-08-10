/** Attempt history screen (UI only). Logic in useHistory. */

import React, { useCallback } from 'react';
import {
  ActivityIndicator,
  FlatList,
  type ListRenderItemInfo,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';
import {
  AppText,
  BandBadge,
  Button,
  Card,
  LineChart,
  Icon,
  ScreenContainer,
  useTheme,
} from '@components';
import { getBandColor, RADIUS, SPACING } from '@constants';
import type { IeltsModule } from '@models';
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

  const renderRow = useCallback(
    ({ item }: ListRenderItemInfo<HistoryRow>) => <HistoryCard row={item} />,
    [],
  );

  const keyExtractor = useCallback((item: HistoryRow) => item.attemptId, []);

  // Everything above the rows, rendered once as the list header rather than
  // per row. Passed as an element rather than a component so it does not
  // remount -- FlatList treats a new component identity as a new header and
  // tears down the chart on every render.
  const header = (
    <>
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
        {MODULES.map(item => {
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
                label: MODULES.find(m => m.value === module)?.label ?? module,
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
          <AppText
            variant="bodyMd"
            color="textSecondary"
            style={styles.emptyBody}
          >
            Complete a {module} practice session and it will appear here with
            your band and score.
          </AppText>
        </Card>
      ) : null}
    </>
  );

  return (
    <ScreenContainer>
      <FlatList
        data={isLoading || error ? [] : rows}
        renderItem={renderRow}
        keyExtractor={keyExtractor}
        ListHeaderComponent={header}
        // Reached before the user hits the bottom, so the next page is
        // arriving while they are still reading the current one.
        onEndReached={hasMore && !isLoadingMore ? loadMore : undefined}
        onEndReachedThreshold={0.5}
        ListFooterComponent={
          hasMore ? (
            <Button
              title={isLoadingMore ? 'Loading…' : 'Load more'}
              variant="secondary"
              onPress={loadMore}
              loading={isLoadingMore}
              style={styles.section}
            />
          ) : null
        }
        // A screenful plus a little. History cards are a fixed shape, so
        // rendering far ahead buys nothing and costs the first paint.
        initialNumToRender={8}
        windowSize={7}
        removeClippedSubviews
        contentContainerStyle={styles.listContent}
        testID="history-list"
      />
    </ScreenContainer>
  );
};

/**
 * Memoised: a list of a hundred attempts re-rendered every card on every
 * parent render, and the rows never change once loaded.
 */
const HistoryCard: React.FC<{ row: HistoryRow }> = React.memo(({ row }) => {
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
});

HistoryCard.displayName = 'HistoryCard';

const styles = StyleSheet.create({
  listContent: { paddingBottom: SPACING.xl },
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
