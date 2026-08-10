/** Practice hub screen (UI only). Logic in usePractice. */

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
import {
  PALETTE,
  RADIUS,
  readableOn,
  SPACING,
  type IconName,
} from '@constants';
import type { AdaptiveDifficultyItem, IeltsModule } from '@models';
import { usePractice } from './usePractice';

interface ModuleMeta {
  module: IeltsModule;
  label: string;
  description: string;
  icon: IconName;
}

const MODULES: ModuleMeta[] = [
  {
    module: 'speaking',
    label: 'Speaking',
    description: 'Cue-card practice scored by the AI examiner',
    icon: 'mic',
  },
  {
    module: 'writing',
    label: 'Writing',
    description: 'Task 2 essay with band + criterion feedback',
    icon: 'writing',
  },
  {
    module: 'reading',
    label: 'Reading',
    description: 'Passages with instant grading and explanations',
    icon: 'reading',
  },
  {
    module: 'listening',
    label: 'Listening',
    description: 'Audio clips with answer timestamps',
    icon: 'listening',
  },
];

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: PALETTE.success,
  medium: PALETTE.warning,
  hard: PALETTE.coral,
};

export const Practice: React.FC = () => {
  const { difficultyByModule, openModule, openMockTest } = usePractice();

  return (
    <ScreenContainer scroll>
      <AppText variant="headlineMobile" style={styles.title}>
        Practice
      </AppText>
      <AppText variant="bodyMd" color="textSecondary" style={styles.subtitle}>
        Choose a module. Difficulty adapts to your recent performance.
      </AppText>

      {MODULES.map(meta => (
        <ModuleCard
          key={meta.module}
          meta={meta}
          level={difficultyByModule[meta.module]}
          onPress={() => openModule(meta.module)}
        />
      ))}
      <Button
        title="Full mock test"
        variant="secondary"
        icon="arrow-right"
        onPress={openMockTest}
        style={styles.mockButton}
        testID="open-mock-test"
      />
    </ScreenContainer>
  );
};

const ModuleCard: React.FC<{
  meta: ModuleMeta;
  level: AdaptiveDifficultyItem | undefined;
  onPress: () => void;
}> = ({ meta, level, onPress }) => {
  const theme = useTheme();
  const color = level ? DIFFICULTY_COLORS[level.difficulty] : undefined;
  return (
    <Pressable onPress={onPress}>
      <Card style={styles.card}>
        <View style={styles.row}>
          <View
            style={[
              styles.icon,
              { backgroundColor: theme.colors.primaryContainer },
            ]}
          >
            <Icon name={meta.icon} size={22} color="primary" />
          </View>
          <View style={styles.textWrap}>
            <View style={styles.labelRow}>
              <AppText variant="titleLg">{meta.label}</AppText>
              {level && color ? (
                <View style={[styles.pill, { backgroundColor: color }]}>
                  <AppText
                    variant="labelSm"
                    style={{ color: readableOn(color) }}
                  >
                    {level.difficulty.toUpperCase()}
                  </AppText>
                </View>
              ) : null}
            </View>
            <AppText variant="bodySm" color="textSecondary" style={styles.desc}>
              {meta.description}
            </AppText>
            {level?.recentBand !== null && level?.recentBand !== undefined ? (
              <AppText variant="labelSm" color="textMuted" style={styles.meta}>
                Recent band {level.recentBand.toFixed(1)}
              </AppText>
            ) : null}
          </View>
          <Icon name="arrow-right" size={20} color="primary" />
        </View>
      </Card>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  mockButton: { marginTop: SPACING.lg },
  title: { marginTop: SPACING.md },
  subtitle: { marginTop: SPACING.xxs, marginBottom: SPACING.md },
  card: { marginBottom: SPACING.md },
  row: { flexDirection: 'row', alignItems: 'center' },
  icon: {
    width: 46,
    height: 46,
    borderRadius: RADIUS.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  textWrap: { flex: 1, marginLeft: SPACING.sm },
  labelRow: { flexDirection: 'row', alignItems: 'center' },
  pill: {
    marginLeft: SPACING.xs,
    paddingHorizontal: SPACING.xs,
    paddingVertical: 2,
    borderRadius: RADIUS.pill,
  },
  desc: { marginTop: 2 },
  meta: { marginTop: SPACING.xxs },
});
