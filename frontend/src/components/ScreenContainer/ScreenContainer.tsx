/** Safe-area screen wrapper with themed background + optional scroll. */

import React from 'react';
import { ScrollView, StyleSheet, View, type ViewStyle } from 'react-native';
import { SafeAreaView, type Edge } from 'react-native-safe-area-context';
import { useTheme } from '../theme/useTheme';
import { SPACING } from '@constants';

interface ScreenContainerProps {
  children: React.ReactNode;
  scroll?: boolean;
  padded?: boolean;
  edges?: readonly Edge[];
  backgroundToken?: 'background' | 'card' | 'surface';
  contentStyle?: ViewStyle;
}

export const ScreenContainer: React.FC<ScreenContainerProps> = ({
  children,
  scroll = false,
  padded = true,
  edges = ['top', 'bottom'],
  backgroundToken = 'background',
  contentStyle,
}) => {
  const theme = useTheme();
  const paddingStyle: ViewStyle = padded
    ? { paddingHorizontal: SPACING.screenPadding }
    : {};

  return (
    <SafeAreaView
      edges={edges}
      style={[styles.safe, { backgroundColor: theme.colors[backgroundToken] }]}
    >
      {scroll ? (
        <ScrollView
          style={styles.flex}
          contentContainerStyle={[
            styles.scrollContent,
            paddingStyle,
            contentStyle,
          ]}
          showsVerticalScrollIndicator={false}
        >
          {children}
        </ScrollView>
      ) : (
        <View style={[styles.flex, paddingStyle, contentStyle]}>
          {children}
        </View>
      )}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1 },
  flex: { flex: 1 },
  scrollContent: { paddingBottom: SPACING.xxl, flexGrow: 1 },
});
