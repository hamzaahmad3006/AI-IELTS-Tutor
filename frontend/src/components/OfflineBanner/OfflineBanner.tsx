/**
 * Offline / sync status strip.
 *
 * Deliberately states the limitation instead of implying live monitoring:
 * connectivity is inferred from whether requests reach the server, so the app
 * cannot know it is offline until something is tried. Claiming otherwise would
 * be a nicer-looking lie.
 */

import React from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { Icon } from '../Icon/Icon';
import { useTheme } from '../theme/useTheme';
import { SPACING } from '@constants';
import { useAppSelector } from '../../redux/hooks';

export const OfflineBanner: React.FC = () => {
  const theme = useTheme();
  const isOffline = useAppSelector(state => state.offline.isOffline);
  const queued = useAppSelector(state => state.offline.queue.length);
  const isSyncing = useAppSelector(state => state.offline.isSyncing);

  // Nothing to say: online with nothing pending.
  if (!isOffline && queued === 0) {
    return null;
  }

  const background = isOffline
    ? theme.colors.warning
    : isSyncing
    ? theme.colors.primary
    : theme.colors.accent;

  const message = isOffline
    ? queued > 0
      ? `Offline — ${queued} change${
          queued === 1 ? '' : 's'
        } saved on this device`
      : 'Offline — changes will be saved until you reconnect'
    : isSyncing
    ? 'Syncing your changes…'
    : `${queued} change${queued === 1 ? '' : 's'} waiting to sync`;

  return (
    <View
      style={[styles.banner, { backgroundColor: background }]}
      accessibilityRole="alert"
      testID="offline-banner"
    >
      <Icon name={isOffline ? 'info' : 'timer'} size={14} color="textInverse" />
      <AppText variant="labelSm" color="textInverse" style={styles.text}>
        {message}
      </AppText>
    </View>
  );
};

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    paddingVertical: 6,
    paddingHorizontal: SPACING.md,
  },
  text: { flex: 1 },
});
