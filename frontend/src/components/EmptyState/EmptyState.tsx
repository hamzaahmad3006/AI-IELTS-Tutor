/**
 * The "nothing to show" surface, in its three honest flavours.
 *
 * `empty`   — worked fine, there is genuinely no data yet.
 * `error`   — the request failed; offer a retry.
 * `offline` — the device could not reach the API at all.
 *
 * These are deliberately distinct: telling a new user "something went wrong"
 * when their account is simply new is worse than saying nothing.
 */

import React from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { Button } from '../Button/Button';
import { Icon } from '../Icon/Icon';
import { SPACING, type IconName, type ThemeColors } from '@constants';

export type EmptyStateVariant = 'empty' | 'error' | 'offline';

interface EmptyStateProps {
  variant?: EmptyStateVariant;
  title: string;
  message?: string;
  /** Omitted for `empty`, where there is nothing to retry. */
  actionLabel?: string;
  onAction?: () => void;
  icon?: IconName;
  testID?: string;
}

const DEFAULTS: Record<
  EmptyStateVariant,
  { icon: IconName; color: keyof ThemeColors }
> = {
  empty: { icon: 'sparkle', color: 'primary' },
  error: { icon: 'info', color: 'error' },
  offline: { icon: 'info', color: 'warning' },
};

export const EmptyState: React.FC<EmptyStateProps> = ({
  variant = 'empty',
  title,
  message,
  actionLabel,
  onAction,
  icon,
  testID,
}) => {
  const preset = DEFAULTS[variant];
  return (
    <View style={styles.wrap} testID={testID ?? `empty-state-${variant}`}>
      <Icon name={icon ?? preset.icon} size={44} color={preset.color} />
      <AppText variant="titleLg" align="center" style={styles.title}>
        {title}
      </AppText>
      {message ? (
        <AppText variant="bodyMd" color="textSecondary" align="center">
          {message}
        </AppText>
      ) : null}
      {actionLabel && onAction ? (
        <Button
          title={actionLabel}
          onPress={onAction}
          fullWidth={false}
          style={styles.action}
        />
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: SPACING.lg,
  },
  title: { marginTop: SPACING.md, marginBottom: SPACING.xs },
  action: { marginTop: SPACING.lg },
});
