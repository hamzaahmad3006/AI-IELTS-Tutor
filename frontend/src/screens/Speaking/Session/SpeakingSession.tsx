/** Speaking session start screen (UI only). Logic in useSpeakingSession. */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import {
  AppText,
  Button,
  Card,
  Icon,
  ScreenContainer,
  useTheme,
} from '@components';
import { RADIUS, SPACING } from '@constants';
import { useSpeakingSession } from './useSpeakingSession';

export const SpeakingSession: React.FC = () => {
  const theme = useTheme();
  const { options, selected, select, start, onBack } = useSpeakingSession();

  return (
    <ScreenContainer scroll>
      <View style={styles.header}>
        <Pressable
          onPress={onBack}
          accessibilityRole="button"
          accessibilityLabel="Back"
        >
          <Icon name="back" size={22} color="primary" />
        </Pressable>
        <AppText variant="titleLg" style={styles.headerTitle}>
          Speaking
        </AppText>
      </View>

      <AppText variant="headlineMobile" style={styles.title}>
        What would you like to practise?
      </AppText>

      {options.map(option => {
        const isSelected = selected === option.choice;
        return (
          <Pressable
            key={option.choice}
            onPress={() => select(option.choice)}
            accessibilityRole="radio"
            accessibilityState={{ selected: isSelected }}
            testID={`session-${option.choice}`}
          >
            <Card
              style={[
                styles.option,
                isSelected && {
                  borderColor: theme.colors.primary,
                  borderWidth: 2,
                },
              ]}
            >
              <View style={styles.optionHead}>
                <AppText variant="bodyMd">{option.title}</AppText>
                <AppText variant="labelSm" color="textMuted">
                  {option.minutes}
                </AppText>
              </View>
              <AppText variant="labelSm" color="textSecondary">
                {option.subtitle}
              </AppText>
            </Card>
          </Pressable>
        );
      })}

      <Card style={styles.notice} backgroundToken="cardAlt">
        <AppText variant="labelMd" color="textSecondary">
          HOW YOU ANSWER
        </AppText>
        {/* Stated up front rather than discovered on the next screen. Asking
            for microphone access we cannot yet use would be worse than saying
            plainly that answers are typed for now. */}
        <AppText
          variant="bodySm"
          color="textSecondary"
          style={styles.noticeBody}
        >
          Answers are typed for now, and scored on what you say rather than how
          you sound. Live voice recording is not enabled yet, so the app does
          not ask for microphone access.
        </AppText>
      </Card>

      <Button title="Start session" onPress={start} style={styles.start} />
    </ScreenContainer>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    marginBottom: SPACING.md,
  },
  headerTitle: { flex: 1 },
  title: { marginBottom: SPACING.md },
  option: { marginTop: SPACING.sm, borderRadius: RADIUS.card },
  optionHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 2,
  },
  notice: { marginTop: SPACING.lg },
  noticeBody: { marginTop: SPACING.xs },
  start: { marginTop: SPACING.lg },
});
