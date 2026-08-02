/** Word diff and highlighted-transcript rendering. */

import React from 'react';
import { fireEvent, screen } from '@testing-library/react-native';
import { renderWithProviders as render } from '../../testUtils/renderWithProviders';
import { diffWords, summariseDiff } from '../HighlightedText/diff';
import {
  HighlightedText,
  type TextIssue,
} from '../HighlightedText/HighlightedText';

describe('diffWords', () => {
  it('marks everything unchanged for identical text', () => {
    const tokens = diffWords('the cat sat', 'the cat sat');
    expect(tokens.every((t) => t.op === 'same')).toBe(true);
  });

  it('detects a replaced word', () => {
    const tokens = diffWords('it help me', 'it helps me');
    expect(tokens.map((t) => t.op)).toContain('removed');
    expect(tokens.map((t) => t.op)).toContain('added');
    const removed = tokens.find((t) => t.op === 'removed');
    const added = tokens.find((t) => t.op === 'added');
    expect(removed?.text.trim()).toBe('help');
    expect(added?.text.trim()).toBe('helps');
  });

  it('treats punctuation-only changes as unchanged', () => {
    // Otherwise every sentence would light up as edited and the real changes
    // would be lost in the noise.
    const tokens = diffWords('Hello world', 'Hello, world.');
    expect(tokens.every((t) => t.op === 'same')).toBe(true);
  });

  it('handles insertion at the end', () => {
    const tokens = diffWords('one two', 'one two three');
    const added = tokens.filter((t) => t.op === 'added');
    expect(added).toHaveLength(1);
    expect(added[0].text.trim()).toBe('three');
  });

  it('handles an empty original', () => {
    const tokens = diffWords('', 'brand new text');
    expect(tokens).toHaveLength(1);
    expect(tokens[0].op).toBe('added');
  });

  it('merges consecutive runs into one token', () => {
    // One node per change, not one per word.
    const tokens = diffWords('a b c d', 'x y z d');
    expect(tokens.filter((t) => t.op === 'removed')).toHaveLength(1);
    expect(tokens.filter((t) => t.op === 'added')).toHaveLength(1);
  });

  it('summarises word counts per operation', () => {
    const summary = summariseDiff(diffWords('one two', 'one two three'));
    expect(summary).toEqual({ added: 1, removed: 0, unchanged: 2 });
  });
});

describe('HighlightedText', () => {
  const text = 'I think it help me a lot every day.';
  const issues: TextIssue[] = [
    {
      start: text.indexOf('it help me'),
      end: text.indexOf('it help me') + 'it help me'.length,
      quote: 'it help me',
      tag: 'grammatical_range',
      note: 'Subject-verb agreement.',
    },
  ];

  it('renders the flagged span and its note', () => {
    render(
      <HighlightedText
        text={text}
        issues={issues}
        activeIndex={null}
        onSelectIssue={jest.fn()}
        testID="ht"
      />,
    );
    expect(screen.getByTestId('ht')).toBeTruthy();
    expect(screen.getByTestId('highlight-0')).toBeTruthy();
    expect(screen.getByText('Subject-verb agreement.')).toBeTruthy();
    // The tag is shown readably rather than as a raw snake_case key.
    expect(screen.getByText('grammatical range')).toBeTruthy();
  });

  it('reports which issue was tapped so the caller can jump to it', () => {
    const onSelect = jest.fn();
    render(
      <HighlightedText
        text={text}
        issues={issues}
        activeIndex={null}
        onSelectIssue={onSelect}
      />,
    );
    fireEvent.press(screen.getByTestId('highlight-0'));
    expect(onSelect).toHaveBeenCalledWith(0);

    fireEvent.press(screen.getByTestId('issue-note-0'));
    expect(onSelect).toHaveBeenCalledTimes(2);
  });

  it('renders plain text when nothing is flagged', () => {
    render(
      <HighlightedText
        text={text}
        issues={[]}
        activeIndex={null}
        onSelectIssue={jest.fn()}
        testID="plain"
      />,
    );
    expect(screen.getByTestId('plain')).toBeTruthy();
    expect(screen.queryByTestId('highlight-0')).toBeNull();
  });
});
