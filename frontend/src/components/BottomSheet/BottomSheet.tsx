/**
 * Slide-up sheet built on React Native's own `Modal`.
 *
 * Uses `Modal` rather than an absolutely-positioned overlay so the sheet sits
 * above the navigator and the OS back button dismisses it for free — an overlay
 * inside the screen would be trapped under the tab bar and would swallow the
 * hardware back press.
 */

import React from 'react';
import {
  Animated,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { AppText } from '../AppText/AppText';
import { useTheme } from '../theme/useTheme';
import { RADIUS, SPACING } from '../../constants';

interface BottomSheetProps {
  visible: boolean;
  onClose: () => void;
  title?: string;
  /** Blocks backdrop/back dismissal — for a choice the user must resolve. */
  dismissable?: boolean;
  children: React.ReactNode;
  testID?: string;
}

export const BottomSheet: React.FC<BottomSheetProps> = ({
  visible,
  onClose,
  title,
  dismissable = true,
  children,
  testID,
}) => {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const slide = React.useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    Animated.timing(slide, {
      toValue: visible ? 1 : 0,
      duration: 200,
      useNativeDriver: true,
    }).start();
  }, [visible, slide]);

  const requestClose = React.useCallback((): void => {
    if (dismissable) {
      onClose();
    }
  }, [dismissable, onClose]);

  const translateY = slide.interpolate({
    inputRange: [0, 1],
    outputRange: [320, 0],
  });

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      // Android hardware back. Non-dismissable sheets deliberately ignore it.
      onRequestClose={requestClose}
      testID={testID}
    >
      <View style={styles.fill}>
        <Pressable
          style={[styles.backdrop, { backgroundColor: theme.colors.scrim }]}
          onPress={requestClose}
          accessibilityRole="button"
          accessibilityLabel="Close"
          testID="bottom-sheet-backdrop"
        />
        <Animated.View
          style={[
            styles.sheet,
            {
              backgroundColor: theme.colors.card,
              paddingBottom: insets.bottom + SPACING.md,
              transform: [{ translateY }],
            },
          ]}
        >
          <View
            style={[styles.grabber, { backgroundColor: theme.colors.outline }]}
          />
          {title ? (
            <AppText variant="titleLg" style={styles.title}>
              {title}
            </AppText>
          ) : null}
          <ScrollView
            bounces={false}
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.body}
          >
            {children}
          </ScrollView>
        </Animated.View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  fill: { flex: 1, justifyContent: 'flex-end' },
  backdrop: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 },
  sheet: {
    borderTopLeftRadius: RADIUS.lg,
    borderTopRightRadius: RADIUS.lg,
    paddingHorizontal: SPACING.md,
    paddingTop: SPACING.sm,
    maxHeight: '85%',
  },
  grabber: {
    alignSelf: 'center',
    width: 40,
    height: 4,
    borderRadius: 2,
    opacity: 0.4,
    marginBottom: SPACING.sm,
  },
  title: { marginBottom: SPACING.sm },
  body: { paddingBottom: SPACING.sm },
});
