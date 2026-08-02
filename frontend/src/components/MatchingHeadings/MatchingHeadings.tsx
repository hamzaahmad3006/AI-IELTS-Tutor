/**
 * Matching-headings task: assign one heading to each paragraph.
 *
 * Tap-to-assign rather than literal drag-and-drop. Dragging a small target
 * across a phone screen is error-prone, and it is unusable with a screen
 * reader — there is no accessible drag gesture. Tapping a heading and then a
 * paragraph (or the reverse) expresses the same intent, works one-handed, and
 * is fully operable by assistive tech.
 *
 * Headings are unique, as in the real task: a placed heading leaves the bank, so
 * it cannot be used twice. To move one, tap its slot to lift it off, then place
 * it again.
 */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { Card } from '../Card/Card';
import { useTheme } from '../theme/useTheme';
import { RADIUS, SPACING } from '../../constants';

export interface MatchingSlot {
  /** Question id the assignment is recorded against. */
  id: string;
  /** Paragraph label shown on the slot, e.g. "Paragraph A". */
  label: string;
}

interface MatchingHeadingsProps {
  headings: string[];
  slots: MatchingSlot[];
  /** questionId -> chosen heading. */
  assignments: Record<string, string | undefined>;
  onAssign: (questionId: string, heading: string | null) => void;
  testID?: string;
}

export const MatchingHeadings: React.FC<MatchingHeadingsProps> = ({
  headings,
  slots,
  assignments,
  onAssign,
  testID,
}) => {
  const theme = useTheme();
  const [pendingHeading, setPendingHeading] = React.useState<string | null>(null);

  const ownerOf = (heading: string): string | undefined =>
    slots.find((slot) => assignments[slot.id] === heading)?.id;

  // Only unplaced headings are rendered, so this always receives a free one.
  // Tapping the same heading twice cancels, rather than trapping the user in a
  // pending state with no way out.
  const chooseHeading = (heading: string): void => {
    setPendingHeading((current) => (current === heading ? null : heading));
  };

  const chooseSlot = (slotId: string): void => {
    if (pendingHeading === null) {
      // No heading in hand: tapping a filled slot empties it.
      if (assignments[slotId]) {
        onAssign(slotId, null);
      }
      return;
    }
    onAssign(slotId, pendingHeading);
    setPendingHeading(null);
  };

  const unplaced = headings.filter((heading) => !ownerOf(heading));

  return (
    <View testID={testID ?? 'matching-headings'}>
      <Card style={styles.card}>
        <AppText variant="labelMd" color="textSecondary">
          HEADINGS
        </AppText>
        <AppText variant="labelSm" color="textMuted" style={styles.hint}>
          {pendingHeading
            ? 'Now tap the paragraph it belongs to.'
            : 'Tap a heading, then tap its paragraph.'}
        </AppText>

        {unplaced.length === 0 ? (
          <AppText variant="labelSm" color="textMuted">
            All headings placed.
          </AppText>
        ) : null}

        <View style={styles.headingList}>
          {unplaced.map((heading) => {
            const isPending = pendingHeading === heading;
            return (
              <Pressable
                key={heading}
                onPress={() => chooseHeading(heading)}
                accessibilityRole="button"
                accessibilityState={{ selected: isPending }}
                accessibilityLabel={`Heading: ${heading}`}
                testID={`heading-${heading}`}
                style={[
                  styles.heading,
                  {
                    borderColor: isPending
                      ? theme.colors.primary
                      : theme.colors.border,
                    backgroundColor: isPending
                      ? theme.colors.primaryContainer
                      : theme.colors.card,
                  },
                ]}
              >
                <AppText variant="bodySm">{heading}</AppText>
              </Pressable>
            );
          })}
        </View>
      </Card>

      {slots.map((slot) => {
        const assigned = assignments[slot.id];
        return (
          <Pressable
            key={slot.id}
            onPress={() => chooseSlot(slot.id)}
            accessibilityRole="button"
            accessibilityLabel={
              assigned
                ? `${slot.label}, currently ${assigned}. Tap to change.`
                : `${slot.label}, no heading yet.`
            }
            testID={`slot-${slot.id}`}
            style={[
              styles.slot,
              {
                borderColor: assigned
                  ? theme.colors.primary
                  : pendingHeading
                    ? theme.colors.accent
                    : theme.colors.outlineVariant,
                borderStyle: assigned ? 'solid' : 'dashed',
                backgroundColor: theme.colors.card,
              },
            ]}
          >
            <AppText variant="labelSm" color="textMuted">
              {slot.label}
            </AppText>
            <AppText
              variant="bodyMd"
              color={assigned ? 'textPrimary' : 'textMuted'}
            >
              {assigned ?? 'Tap to place a heading'}
            </AppText>
          </Pressable>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  card: { marginTop: SPACING.sm },
  hint: { marginTop: 2, marginBottom: SPACING.sm },
  headingList: { gap: SPACING.sm },
  heading: {
    borderWidth: 1,
    borderRadius: RADIUS.md,
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.md,
  },
  slot: {
    borderWidth: 2,
    borderRadius: RADIUS.card,
    padding: SPACING.md,
    marginTop: SPACING.sm,
    gap: 2,
  },
});
