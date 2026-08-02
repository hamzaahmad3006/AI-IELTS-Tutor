/**
 * Renders text with AI-flagged spans marked, plus a diff renderer.
 *
 * Spans arrive as character offsets already validated against this exact text
 * by the API, so nothing is searched for here — searching client-side is how
 * highlights end up over the wrong words.
 */

import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { useTheme } from '../theme/useTheme';
import { RADIUS, SPACING } from '../../constants';
import type { DiffToken } from './diff';

export interface TextIssue {
  start: number;
  end: number;
  quote: string;
  tag: string;
  note: string;
}

interface HighlightedTextProps {
  text: string;
  issues: TextIssue[];
  /** Index of the issue currently focused, or null. */
  activeIndex: number | null;
  onSelectIssue: (index: number) => void;
  testID?: string;
}

export const HighlightedText: React.FC<HighlightedTextProps> = ({
  text,
  issues,
  activeIndex,
  onSelectIssue,
  testID,
}) => {
  const theme = useTheme();

  // Walk the text once, emitting plain and highlighted runs in order.
  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  issues.forEach((issue, index) => {
    if (issue.start > cursor) {
      nodes.push(
        <AppText key={`plain-${cursor}`} variant="bodyMd">
          {text.slice(cursor, issue.start)}
        </AppText>,
      );
    }
    const isActive = activeIndex === index;
    nodes.push(
      <AppText
        key={`issue-${index}`}
        variant="bodyMd"
        onPress={() => onSelectIssue(index)}
        style={{
          backgroundColor: isActive
            ? theme.colors.errorHighlight
            : theme.colors.suggestionHighlight,
        }}
        testID={`highlight-${index}`}
      >
        {text.slice(issue.start, issue.end)}
      </AppText>,
    );
    cursor = issue.end;
  });
  if (cursor < text.length) {
    nodes.push(
      <AppText key="plain-tail" variant="bodyMd">
        {text.slice(cursor)}
      </AppText>,
    );
  }

  return (
    <View testID={testID}>
      <AppText variant="bodyMd">{nodes}</AppText>

      {issues.map((issue, index) => (
        <Pressable
          key={`note-${index}`}
          onPress={() => onSelectIssue(index)}
          accessibilityRole="button"
          accessibilityState={{ selected: activeIndex === index }}
          accessibilityLabel={`Issue ${index + 1}: ${issue.note}`}
          testID={`issue-note-${index}`}
          style={[
            styles.note,
            {
              borderColor:
                activeIndex === index
                  ? theme.colors.primary
                  : theme.colors.outlineVariant,
              backgroundColor: theme.colors.cardAlt,
            },
          ]}
        >
          <AppText variant="labelSm" color="primary">
            {issue.tag.replace(/_/g, ' ')}
          </AppText>
          <AppText variant="bodySm" color="textSecondary">
            {issue.note}
          </AppText>
        </Pressable>
      ))}
    </View>
  );
};

interface DiffTextProps {
  tokens: DiffToken[];
  testID?: string;
}

/** Renders a word diff: removals struck through, additions emphasised. */
export const DiffText: React.FC<DiffTextProps> = ({ tokens, testID }) => {
  const theme = useTheme();
  return (
    <View testID={testID}>
      <AppText variant="bodyMd">
        {tokens.map((token, index) => {
          if (token.op === 'same') {
            return (
              <AppText key={index} variant="bodyMd">
                {token.text}
              </AppText>
            );
          }
          const removed = token.op === 'removed';
          return (
            <AppText
              key={index}
              variant="bodyMd"
              testID={`diff-${token.op}-${index}`}
              style={{
                backgroundColor: removed
                  ? theme.colors.errorHighlight
                  : theme.colors.strongHighlight,
                textDecorationLine: removed ? 'line-through' : 'none',
              }}
            >
              {token.text}
            </AppText>
          );
        })}
      </AppText>
    </View>
  );
};

const styles = StyleSheet.create({
  note: {
    borderWidth: 1,
    borderRadius: RADIUS.md,
    padding: SPACING.sm,
    marginTop: SPACING.sm,
    gap: 2,
  },
});
