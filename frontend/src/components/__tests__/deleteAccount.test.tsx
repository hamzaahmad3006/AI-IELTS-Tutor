/**
 * The destructive-confirmation path. These guard the one action in the app
 * that cannot be undone.
 */

import React from 'react';
import { fireEvent, screen } from '@testing-library/react-native';
import { renderWithProviders as render } from '../../testUtils/renderWithProviders';
import { DeleteAccountSheet } from '../DeleteAccountSheet/DeleteAccountSheet';

describe('DeleteAccountSheet', () => {
  it('states plainly what is lost', () => {
    render(
      <DeleteAccountSheet visible onClose={jest.fn()} onConfirm={jest.fn()} />,
    );
    expect(screen.getByText(/cannot be undone/)).toBeTruthy();
  });

  it('stays disarmed until the confirmation word is typed', () => {
    const onConfirm = jest.fn();
    render(
      <DeleteAccountSheet visible onClose={jest.fn()} onConfirm={onConfirm} />,
    );

    fireEvent.press(screen.getByTestId('delete-confirm-button'));
    expect(onConfirm).not.toHaveBeenCalled();

    // Close, but not the word.
    fireEvent.changeText(screen.getByTestId('delete-confirm-input'), 'DELET');
    fireEvent.press(screen.getByTestId('delete-confirm-button'));
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('arms once the word matches', () => {
    const onConfirm = jest.fn();
    render(
      <DeleteAccountSheet visible onClose={jest.fn()} onConfirm={onConfirm} />,
    );
    fireEvent.changeText(screen.getByTestId('delete-confirm-input'), 'DELETE');
    fireEvent.press(screen.getByTestId('delete-confirm-button'));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('accepts the word in any case, with stray whitespace', () => {
    const onConfirm = jest.fn();
    render(
      <DeleteAccountSheet visible onClose={jest.fn()} onConfirm={onConfirm} />,
    );
    fireEvent.changeText(screen.getByTestId('delete-confirm-input'), ' delete ');
    fireEvent.press(screen.getByTestId('delete-confirm-button'));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('ignores a backdrop tap', () => {
    // A stray tap must not land anywhere near this action.
    const onClose = jest.fn();
    render(
      <DeleteAccountSheet visible onClose={onClose} onConfirm={jest.fn()} />,
    );
    fireEvent.press(screen.getByTestId('bottom-sheet-backdrop'));
    expect(onClose).not.toHaveBeenCalled();
  });

  it('offers an explicit way out', () => {
    const onClose = jest.fn();
    render(
      <DeleteAccountSheet visible onClose={onClose} onConfirm={jest.fn()} />,
    );
    fireEvent.press(screen.getByText('Cancel'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('cannot be double-submitted while deleting', () => {
    const onConfirm = jest.fn();
    render(
      <DeleteAccountSheet
        visible
        isDeleting
        onClose={jest.fn()}
        onConfirm={onConfirm}
      />,
    );
    fireEvent.changeText(screen.getByTestId('delete-confirm-input'), 'DELETE');
    fireEvent.press(screen.getByTestId('delete-confirm-button'));
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
