/**
 * Word-level diff, used to show what an improved essay actually changed.
 *
 * A plain "here is a better version" is not teaching — the learner has to spot
 * the edits themselves. This marks them.
 *
 * Classic LCS: O(n·m) in words. Essays here are capped at 8000 characters by
 * the API, so the table stays small enough that the simple algorithm is the
 * right trade against pulling in a dependency.
 */

export type DiffOp = 'same' | 'added' | 'removed';

export interface DiffToken {
  op: DiffOp;
  text: string;
}

/** Split into words while keeping the whitespace that follows each one. */
const tokenize = (text: string): string[] => text.match(/\S+\s*/g) ?? [];

const normalise = (token: string): string =>
  token
    .trim()
    .toLowerCase()
    .replace(/[.,;:!?"'()]/g, '');

export const diffWords = (before: string, after: string): DiffToken[] => {
  const a = tokenize(before);
  const b = tokenize(after);

  // lengths[i][j] = LCS length of a[i:] and b[j:]
  const lengths: number[][] = Array.from({ length: a.length + 1 }, () =>
    new Array<number>(b.length + 1).fill(0),
  );
  for (let i = a.length - 1; i >= 0; i -= 1) {
    for (let j = b.length - 1; j >= 0; j -= 1) {
      lengths[i][j] =
        normalise(a[i]) === normalise(b[j])
          ? lengths[i + 1][j + 1] + 1
          : Math.max(lengths[i + 1][j], lengths[i][j + 1]);
    }
  }

  const tokens: DiffToken[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (normalise(a[i]) === normalise(b[j])) {
      // Keep the improved wording when only punctuation or case changed, so
      // the learner reads the corrected form.
      tokens.push({ op: 'same', text: b[j] });
      i += 1;
      j += 1;
    } else if (lengths[i + 1][j] >= lengths[i][j + 1]) {
      tokens.push({ op: 'removed', text: a[i] });
      i += 1;
    } else {
      tokens.push({ op: 'added', text: b[j] });
      j += 1;
    }
  }
  while (i < a.length) {
    tokens.push({ op: 'removed', text: a[i] });
    i += 1;
  }
  while (j < b.length) {
    tokens.push({ op: 'added', text: b[j] });
    j += 1;
  }

  // Merge runs so the renderer emits one node per change, not one per word.
  return tokens.reduce<DiffToken[]>((merged, token) => {
    const last = merged[merged.length - 1];
    if (last && last.op === token.op) {
      last.text += token.text;
      return merged;
    }
    merged.push({ ...token });
    return merged;
  }, []);
};

export interface DiffSummary {
  added: number;
  removed: number;
  unchanged: number;
}

/** Word counts per operation, for a one-line "what changed" summary. */
export const summariseDiff = (tokens: DiffToken[]): DiffSummary =>
  tokens.reduce<DiffSummary>(
    (summary, token) => {
      const words = token.text.trim().split(/\s+/).filter(Boolean).length;
      if (token.op === 'added') {
        summary.added += words;
      } else if (token.op === 'removed') {
        summary.removed += words;
      } else {
        summary.unchanged += words;
      }
      return summary;
    },
    { added: 0, removed: 0, unchanged: 0 },
  );
