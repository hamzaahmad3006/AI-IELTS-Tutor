/**
 * Renders the toast queue above everything else.
 *
 * Mounted once, near the app root, so any screen or the axios interceptor can
 * raise a message by dispatching `showToast`. Only the front of the queue is
 * shown: stacked bars cover the UI they are commenting on.
 */

import React from 'react';
import { Animated, Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { AppText } from '../AppText/AppText';
import { Icon } from '../Icon/Icon';
import { useTheme } from '../theme/useTheme';
import { RADIUS, SPACING, type IconName } from '@constants';
import { useAppDispatch, useAppSelector } from '@redux/hooks';
import { dismissToast, type ToastTone } from '@redux/slices/toastSlice';

const ICON_FOR: Record<ToastTone, IconName> = {
  success: 'check',
  error: 'info',
  info: 'info',
};

export const ToastHost: React.FC = () => {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const dispatch = useAppDispatch();
  const toast = useAppSelector(state => state.toast.queue[0]);
  const opacity = React.useRef(new Animated.Value(0)).current;

  const id = toast?.id;
  const durationMs = toast?.durationMs;

  React.useEffect(() => {
    if (id === undefined || durationMs === undefined) {
      return;
    }
    opacity.setValue(0);
    Animated.timing(opacity, {
      toValue: 1,
      duration: 180,
      useNativeDriver: true,
    }).start();

    const timer = setTimeout(() => {
      dispatch(dismissToast(id));
    }, durationMs);
    // Clearing on id change is what prevents a queued toast from inheriting the
    // previous one's remaining time.
    return () => clearTimeout(timer);
  }, [id, durationMs, dispatch, opacity]);

  if (!toast) {
    return null;
  }

  const background =
    toast.tone === 'error'
      ? theme.colors.error
      : toast.tone === 'success'
      ? theme.colors.success
      : theme.colors.onSurface;

  return (
    <View
      style={[styles.wrap, { bottom: insets.bottom + SPACING.lg }]}
      pointerEvents="box-none"
      testID="toast-host"
    >
      <Animated.View style={{ opacity, width: '100%' }}>
        <Pressable
          onPress={() => dispatch(dismissToast(toast.id))}
          accessibilityRole="button"
          accessibilityLabel={`Dismiss: ${toast.message}`}
          style={[styles.toast, { backgroundColor: background }]}
          testID={`toast-${toast.tone}`}
        >
          <Icon name={ICON_FOR[toast.tone]} size={18} color="textInverse" />
          <AppText variant="bodySm" color="textInverse" style={styles.message}>
            {toast.message}
          </AppText>
        </Pressable>
      </Animated.View>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    left: SPACING.md,
    right: SPACING.md,
    alignItems: 'center',
  },
  toast: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.md,
    borderRadius: RADIUS.md,
  },
  message: { flex: 1 },
});
