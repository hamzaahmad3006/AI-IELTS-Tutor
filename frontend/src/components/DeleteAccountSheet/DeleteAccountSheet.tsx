/**
 * Irreversible account deletion, behind a typed confirmation.
 *
 * The sheet is deliberately not dismissable by backdrop tap: a stray tap while
 * this is open should not be able to land anywhere near the delete button.
 * Requiring the word DELETE is friction on purpose — this erases every attempt,
 * band and piece of progress the learner has, and nothing brings it back.
 */

import React from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { BottomSheet } from '../BottomSheet/BottomSheet';
import { Button } from '../Button/Button';
import { Input } from '../Input/Input';
import { SPACING } from '../../constants';

const CONFIRM_WORD = 'DELETE';

interface DeleteAccountSheetProps {
  visible: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isDeleting?: boolean;
}

export const DeleteAccountSheet: React.FC<DeleteAccountSheetProps> = ({
  visible,
  onClose,
  onConfirm,
  isDeleting = false,
}) => {
  const [typed, setTyped] = React.useState<string>('');

  // Clear on open so a previous confirmation cannot arm the button.
  React.useEffect(() => {
    if (visible) {
      setTyped('');
    }
  }, [visible]);

  const armed = typed.trim().toUpperCase() === CONFIRM_WORD;

  return (
    <BottomSheet
      visible={visible}
      onClose={onClose}
      title="Delete your account"
      dismissable={false}
    >
      <AppText variant="bodyMd" color="textSecondary">
        This permanently erases your profile, every practice attempt, your band
        history and your saved vocabulary. It cannot be undone.
      </AppText>

      <Input
        label={`Type ${CONFIRM_WORD} to confirm`}
        value={typed}
        onChangeText={setTyped}
        style={styles.input}
        placeholder={CONFIRM_WORD}
        autoCapitalize="characters"
        autoCorrect={false}
        testID="delete-confirm-input"
      />

      <Button
        title={isDeleting ? 'Deleting…' : 'Delete my account'}
        onPress={onConfirm}
        disabled={!armed || isDeleting}
        style={styles.confirm}
        testID="delete-confirm-button"
      />
      <Button
        title="Cancel"
        variant="secondary"
        onPress={onClose}
        disabled={isDeleting}
        style={styles.cancel}
      />
    </BottomSheet>
  );
};

const styles = StyleSheet.create({
  input: { marginTop: SPACING.md },
  confirm: { marginTop: SPACING.md },
  cancel: { marginTop: SPACING.sm },
});
