/**
 * Consent management.
 *
 * Consent is only meaningful if it can be withdrawn as easily as it was given,
 * so both toggles are always editable here — this is not a one-time onboarding
 * gate. AI processing is required for scoring, so turning it off is allowed but
 * states plainly what stops working rather than silently degrading.
 */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { BottomSheet } from '../BottomSheet/BottomSheet';
import { Button } from '../Button/Button';
import { Icon } from '../Icon/Icon';
import { useTheme } from '../theme/useTheme';
import { RADIUS, SPACING } from '@constants';

export interface ConsentValues {
  consentAi: boolean;
  consentVoice: boolean;
}

interface ConsentSheetProps {
  visible: boolean;
  value: ConsentValues;
  onClose: () => void;
  onSave: (next: ConsentValues) => void;
  isSaving?: boolean;
}

interface RowProps {
  label: string;
  description: string;
  checked: boolean;
  onToggle: () => void;
  testID: string;
}

const ConsentRow: React.FC<RowProps> = ({
  label,
  description,
  checked,
  onToggle,
  testID,
}) => {
  const theme = useTheme();
  return (
    <Pressable
      onPress={onToggle}
      accessibilityRole="checkbox"
      accessibilityState={{ checked }}
      accessibilityLabel={label}
      testID={testID}
      style={[styles.row, { borderColor: theme.colors.border }]}
    >
      <View style={styles.rowText}>
        <AppText variant="bodyMd">{label}</AppText>
        <AppText variant="labelSm" color="textSecondary">
          {description}
        </AppText>
      </View>
      <View
        style={[
          styles.box,
          {
            backgroundColor: checked ? theme.colors.accent : 'transparent',
            borderColor: checked ? theme.colors.accent : theme.colors.outline,
          },
        ]}
      >
        {checked ? <Icon name="check" size={14} color="onAccent" /> : null}
      </View>
    </Pressable>
  );
};

export const ConsentSheet: React.FC<ConsentSheetProps> = ({
  visible,
  value,
  onClose,
  onSave,
  isSaving = false,
}) => {
  const [draft, setDraft] = React.useState<ConsentValues>(value);

  // Re-seed whenever the sheet opens, so a cancelled edit does not leak into
  // the next one.
  React.useEffect(() => {
    if (visible) {
      setDraft(value);
    }
  }, [visible, value]);

  const dirty =
    draft.consentAi !== value.consentAi ||
    draft.consentVoice !== value.consentVoice;

  return (
    <BottomSheet visible={visible} onClose={onClose} title="Privacy & consent">
      <ConsentRow
        label="AI processing"
        description="Lets the AI examiner score your answers. Turning this off disables Writing and Speaking feedback."
        checked={draft.consentAi}
        onToggle={() => setDraft(d => ({ ...d, consentAi: !d.consentAi }))}
        testID="consent-ai-row"
      />
      <ConsentRow
        label="Voice recording"
        description="Needed for spoken interview practice. Recordings are used only to score that attempt."
        checked={draft.consentVoice}
        onToggle={() =>
          setDraft(d => ({ ...d, consentVoice: !d.consentVoice }))
        }
        testID="consent-voice-row"
      />

      {!draft.consentAi ? (
        <AppText variant="labelSm" color="warning" style={styles.warning}>
          Without AI processing you can still practise Reading and Listening,
          which are graded without AI.
        </AppText>
      ) : null}

      <Button
        title={isSaving ? 'Saving…' : 'Save'}
        onPress={() => onSave(draft)}
        disabled={!dirty || isSaving}
        style={styles.save}
      />
    </BottomSheet>
  );
};

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.md,
    borderWidth: 1,
    borderRadius: RADIUS.card,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
  },
  rowText: { flex: 1, gap: 2 },
  box: {
    width: 24,
    height: 24,
    borderRadius: RADIUS.sm,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  warning: { marginBottom: SPACING.sm },
  save: { marginTop: SPACING.sm },
});
