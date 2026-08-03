/**
 * Month-grid date picker in a bottom sheet.
 *
 * Hand-rolled rather than using @react-native-community/datetimepicker: that is
 * a native module, so adding it forces a rebuild and cannot be verified on iOS
 * here. This needs no native code and behaves identically on both platforms.
 *
 * Scoped to picking an exam date, so past days are disabled.
 */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { BottomSheet } from '../BottomSheet/BottomSheet';
import { Button } from '../Button/Button';
import { Icon } from '../Icon/Icon';
import { useTheme } from '../theme/useTheme';
import { RADIUS, SPACING } from '@constants';

interface DatePickerSheetProps {
  visible: boolean;
  /** ISO `YYYY-MM-DD`, or null when unset. */
  value: string | null;
  onClose: () => void;
  onSelect: (isoDate: string) => void;
  onClear?: () => void;
  title?: string;
  isSaving?: boolean;
}

const WEEKDAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'] as const;
const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const;

/** Local-time ISO date. `toISOString()` would shift the day across timezones. */
export const toIsoDate = (date: Date): string => {
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
};

const parseIsoDate = (iso: string | null): Date | null => {
  if (!iso) {
    return null;
  }
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d) {
    return null;
  }
  return new Date(y, m - 1, d);
};

/** Days in `month`, padded so the grid starts on a Monday. */
export const buildMonthGrid = (
  year: number,
  month: number,
): (number | null)[] => {
  const first = new Date(year, month, 1);
  // getDay() is Sunday-based; shift so Monday is 0.
  const lead = (first.getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  return [
    ...Array<null>(lead).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
};

export const DatePickerSheet: React.FC<DatePickerSheetProps> = ({
  visible,
  value,
  onClose,
  onSelect,
  onClear,
  title = 'Pick a date',
  isSaving = false,
}) => {
  const theme = useTheme();
  const today = React.useMemo(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  }, []);

  const selected = parseIsoDate(value);
  const [cursor, setCursor] = React.useState<Date>(selected ?? today);

  React.useEffect(() => {
    if (visible) {
      setCursor(parseIsoDate(value) ?? today);
    }
  }, [visible, value, today]);

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const cells = buildMonthGrid(year, month);

  const shiftMonth = (delta: number): void => {
    setCursor(new Date(year, month + delta, 1));
  };

  return (
    <BottomSheet visible={visible} onClose={onClose} title={title}>
      <View style={styles.header}>
        <Pressable
          onPress={() => shiftMonth(-1)}
          accessibilityRole="button"
          accessibilityLabel="Previous month"
          testID="month-prev"
          style={styles.arrow}
        >
          <Icon name="back" size={20} color="primary" />
        </Pressable>
        <AppText variant="bodyMd" testID="month-label">
          {`${MONTHS[month]} ${year}`}
        </AppText>
        <Pressable
          onPress={() => shiftMonth(1)}
          accessibilityRole="button"
          accessibilityLabel="Next month"
          testID="month-next"
          style={[styles.arrow, styles.flip]}
        >
          <Icon name="back" size={20} color="primary" />
        </Pressable>
      </View>

      <View style={styles.grid}>
        {WEEKDAYS.map((day, i) => (
          <View key={`wd-${i}`} style={styles.cell}>
            <AppText variant="labelSm" color="textMuted" align="center">
              {day}
            </AppText>
          </View>
        ))}

        {cells.map((day, i) => {
          if (day === null) {
            return <View key={`pad-${i}`} style={styles.cell} />;
          }
          const date = new Date(year, month, day);
          const isPast = date < today;
          const isSelected = value === toIsoDate(date);
          return (
            <Pressable
              key={`d-${day}`}
              disabled={isPast}
              onPress={() => onSelect(toIsoDate(date))}
              accessibilityRole="button"
              accessibilityState={{ disabled: isPast, selected: isSelected }}
              accessibilityLabel={`${day} ${MONTHS[month]} ${year}`}
              testID={`day-${toIsoDate(date)}`}
              style={[
                styles.cell,
                styles.day,
                isSelected && { backgroundColor: theme.colors.primary },
              ]}
            >
              <AppText
                variant="bodySm"
                align="center"
                // Past days stay visible but obviously inert.
                color={
                  isSelected
                    ? 'textInverse'
                    : isPast
                    ? 'textMuted'
                    : 'textPrimary'
                }
              >
                {String(day)}
              </AppText>
            </Pressable>
          );
        })}
      </View>

      {onClear && value ? (
        <Button
          title={isSaving ? 'Saving…' : 'Clear date'}
          variant="secondary"
          onPress={onClear}
          disabled={isSaving}
          style={styles.clear}
        />
      ) : null}
    </BottomSheet>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: SPACING.sm,
  },
  arrow: { padding: SPACING.sm },
  flip: { transform: [{ rotate: '180deg' }] },
  grid: { flexDirection: 'row', flexWrap: 'wrap' },
  cell: {
    width: `${100 / 7}%`,
    aspectRatio: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  day: { borderRadius: RADIUS.pill },
  clear: { marginTop: SPACING.md },
});
