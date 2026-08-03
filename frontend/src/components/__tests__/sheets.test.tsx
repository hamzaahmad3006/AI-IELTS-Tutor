/**
 * Bottom sheet primitive and the two sheets built on it.
 */

import React from 'react';
import { Text } from 'react-native';
import { fireEvent, screen } from '@testing-library/react-native';
import { renderWithProviders as render } from '../../testUtils/renderWithProviders';
import { BottomSheet } from '../BottomSheet/BottomSheet';
import { ConsentSheet } from '../ConsentSheet/ConsentSheet';
import {
  buildMonthGrid,
  DatePickerSheet,
  toIsoDate,
} from '../DatePickerSheet/DatePickerSheet';

describe('BottomSheet', () => {
  it('renders its children when visible', () => {
    render(
      <BottomSheet visible onClose={jest.fn()} title="Settings">
        <Text>Sheet body</Text>
      </BottomSheet>,
    );
    expect(screen.getByText('Settings')).toBeTruthy();
    expect(screen.getByText('Sheet body')).toBeTruthy();
  });

  it('closes when the backdrop is pressed', () => {
    const onClose = jest.fn();
    render(
      <BottomSheet visible onClose={onClose}>
        <Text>Body</Text>
      </BottomSheet>,
    );
    fireEvent.press(screen.getByTestId('bottom-sheet-backdrop'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('ignores the backdrop when not dismissable', () => {
    // For a choice the user must actually resolve.
    const onClose = jest.fn();
    render(
      <BottomSheet visible onClose={onClose} dismissable={false}>
        <Text>Body</Text>
      </BottomSheet>,
    );
    fireEvent.press(screen.getByTestId('bottom-sheet-backdrop'));
    expect(onClose).not.toHaveBeenCalled();
  });
});

describe('ConsentSheet', () => {
  const value = { consentAi: true, consentVoice: false };

  it('saves only what actually changed', () => {
    const onSave = jest.fn();
    render(
      <ConsentSheet
        visible
        value={value}
        onClose={jest.fn()}
        onSave={onSave}
      />,
    );
    fireEvent.press(screen.getByTestId('consent-voice-row'));
    fireEvent.press(screen.getByText('Save'));
    expect(onSave).toHaveBeenCalledWith({
      consentAi: true,
      consentVoice: true,
    });
  });

  it('keeps Save inert until something changes', () => {
    const onSave = jest.fn();
    render(
      <ConsentSheet
        visible
        value={value}
        onClose={jest.fn()}
        onSave={onSave}
      />,
    );
    fireEvent.press(screen.getByText('Save'));
    expect(onSave).not.toHaveBeenCalled();
  });

  it('says what stops working when AI consent is withdrawn', () => {
    // Withdrawal must be allowed, but not silently degrade the app.
    render(
      <ConsentSheet
        visible
        value={value}
        onClose={jest.fn()}
        onSave={jest.fn()}
      />,
    );
    fireEvent.press(screen.getByTestId('consent-ai-row'));
    expect(screen.getByText(/Reading and Listening/)).toBeTruthy();
  });
});

describe('DatePickerSheet', () => {
  it('pads the grid so the month starts on the right weekday', () => {
    // 1 June 2026 is a Monday -> no leading blanks; 30 days.
    const june = buildMonthGrid(2026, 5);
    expect(june[0]).toBe(1);
    expect(june.filter(d => d !== null)).toHaveLength(30);

    // 1 July 2026 is a Wednesday -> two leading blanks.
    const july = buildMonthGrid(2026, 6);
    expect(july.slice(0, 2)).toEqual([null, null]);
    expect(july[2]).toBe(1);
  });

  it('formats dates in local time', () => {
    // toISOString() would roll this back a day west of UTC.
    expect(toIsoDate(new Date(2026, 0, 1))).toBe('2026-01-01');
    expect(toIsoDate(new Date(2026, 11, 31))).toBe('2026-12-31');
  });

  it('moves between months', () => {
    render(
      <DatePickerSheet
        visible
        value="2026-06-15"
        onClose={jest.fn()}
        onSelect={jest.fn()}
      />,
    );
    expect(screen.getByText('June 2026')).toBeTruthy();
    fireEvent.press(screen.getByTestId('month-next'));
    expect(screen.getByText('July 2026')).toBeTruthy();
    fireEvent.press(screen.getByTestId('month-prev'));
    expect(screen.getByText('June 2026')).toBeTruthy();
  });

  it('offers to clear an existing date', () => {
    const onClear = jest.fn();
    render(
      <DatePickerSheet
        visible
        value="2026-06-15"
        onClose={jest.fn()}
        onSelect={jest.fn()}
        onClear={onClear}
      />,
    );
    fireEvent.press(screen.getByText('Clear date'));
    expect(onClear).toHaveBeenCalledTimes(1);
  });

  it('has nothing to clear when no date is set', () => {
    render(
      <DatePickerSheet
        visible
        value={null}
        onClose={jest.fn()}
        onSelect={jest.fn()}
        onClear={jest.fn()}
      />,
    );
    expect(screen.queryByText('Clear date')).toBeNull();
  });
});
