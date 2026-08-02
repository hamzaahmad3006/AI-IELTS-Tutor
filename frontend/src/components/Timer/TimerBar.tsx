/** Countdown display with start/pause/restart, shared by timed modules. */

import React from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { Button } from '../Button/Button';
import { Card } from '../Card/Card';
import { useTheme } from '../theme/useTheme';
import { SPACING } from '../../constants';
import { formatClock, type TimerState } from './useCountdown';

interface TimerBarProps {
  secondsLeft: number;
  state: TimerState;
  isWarning: boolean;
  onStart: () => void;
  onPause: () => void;
  onReset: () => void;
  /** Shown when the clock runs out. */
  expiredNote?: string;
  testID?: string;
}

export const TimerBar: React.FC<TimerBarProps> = ({
  secondsLeft,
  state,
  isWarning,
  onStart,
  onPause,
  onReset,
  expiredNote = 'Time is up. You can still finish and submit — this is practice.',
  testID,
}) => {
  const theme = useTheme();
  const expired = state === 'expired';
  const color = expired
    ? theme.colors.error
    : isWarning
      ? theme.colors.warning
      : theme.colors.textPrimary;

  return (
    <Card style={styles.card} testID={testID ?? 'practice-timer'}>
      <View style={styles.row}>
        <View>
          <AppText variant="labelMd" color="textSecondary">
            TIME REMAINING
          </AppText>
          <AppText variant="displayLg" style={{ color }} testID="timer-clock">
            {formatClock(secondsLeft)}
          </AppText>
        </View>
        <Button
          title={state === 'running' ? 'Pause' : expired ? 'Restart' : 'Start'}
          variant="secondary"
          fullWidth={false}
          onPress={state === 'running' ? onPause : expired ? onReset : onStart}
          testID="timer-toggle"
        />
      </View>
      {expired ? (
        <AppText variant="labelSm" color="error">
          {expiredNote}
        </AppText>
      ) : null}
    </Card>
  );
};

const styles = StyleSheet.create({
  card: { marginTop: SPACING.sm },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
});
