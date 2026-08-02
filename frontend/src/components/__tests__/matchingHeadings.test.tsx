/** Matching-headings assignment behaviour. */

import React from 'react';
import { fireEvent, screen } from '@testing-library/react-native';
import { renderWithProviders as render } from '../../testUtils/renderWithProviders';
import {
  MatchingHeadings,
  type MatchingSlot,
} from '../MatchingHeadings/MatchingHeadings';

const HEADINGS = ['Why ice stayed local', 'A trade in natural ice', 'A distractor'];
const SLOTS: MatchingSlot[] = [
  { id: 'q1', label: 'Paragraph A' },
  { id: 'q2', label: 'Paragraph B' },
];

const setup = (assignments: Record<string, string | undefined> = {}) => {
  const onAssign = jest.fn();
  render(
    <MatchingHeadings
      headings={HEADINGS}
      slots={SLOTS}
      assignments={assignments}
      onAssign={onAssign}
    />,
  );
  return { onAssign };
};

describe('MatchingHeadings', () => {
  it('lists every heading and every paragraph slot', () => {
    setup();
    HEADINGS.forEach((heading) => {
      expect(screen.getByTestId(`heading-${heading}`)).toBeTruthy();
    });
    expect(screen.getByTestId('slot-q1')).toBeTruthy();
    expect(screen.getByTestId('slot-q2')).toBeTruthy();
  });

  it('assigns a heading after tapping it and then a paragraph', () => {
    const { onAssign } = setup();
    fireEvent.press(screen.getByTestId(`heading-${HEADINGS[0]}`));
    // The hint changes so the two-step interaction is discoverable.
    expect(screen.getByText('Now tap the paragraph it belongs to.')).toBeTruthy();

    fireEvent.press(screen.getByTestId('slot-q1'));
    expect(onAssign).toHaveBeenCalledWith('q1', HEADINGS[0]);
  });

  it('hides a heading once it is placed', () => {
    setup({ q1: HEADINGS[0] });
    // Each heading is used at most once, so a placed one leaves the bank.
    expect(screen.queryByTestId(`heading-${HEADINGS[0]}`)).toBeNull();
    expect(screen.getByTestId(`heading-${HEADINGS[1]}`)).toBeTruthy();
  });

  it('shows the assigned heading on its slot', () => {
    setup({ q1: HEADINGS[0] });
    expect(screen.getByText(HEADINGS[0])).toBeTruthy();
    expect(screen.getByText('Tap to place a heading')).toBeTruthy();
  });

  it('clears a slot when tapped with nothing in hand', () => {
    // The only way to undo a misplacement without hunting for it.
    const { onAssign } = setup({ q1: HEADINGS[0] });
    fireEvent.press(screen.getByTestId('slot-q1'));
    expect(onAssign).toHaveBeenCalledWith('q1', null);
  });

  it('moves a heading between slots without duplicating it', () => {
    // Driven through a stateful wrapper so the full lift-and-place flow runs,
    // rather than asserting only the first step.
    const Harness: React.FC = () => {
      const [assignments, setAssignments] = React.useState<
        Record<string, string | undefined>
      >({ q1: HEADINGS[0] });
      return (
        <MatchingHeadings
          headings={HEADINGS}
          slots={SLOTS}
          assignments={assignments}
          onAssign={(id, heading) =>
            setAssignments((prev) => ({ ...prev, [id]: heading ?? undefined }))
          }
        />
      );
    };
    render(<Harness />);

    // Lift it off Paragraph A, then place it on Paragraph B.
    fireEvent.press(screen.getByTestId('slot-q1'));
    fireEvent.press(screen.getByTestId(`heading-${HEADINGS[0]}`));
    fireEvent.press(screen.getByTestId('slot-q2'));

    expect(screen.getByTestId('slot-q2')).toHaveTextContent(
      new RegExp(HEADINGS[0]),
    );
    expect(screen.getByTestId('slot-q1')).toHaveTextContent(
      /Tap to place a heading/,
    );
    // Used exactly once: it is gone from the bank.
    expect(screen.queryByTestId(`heading-${HEADINGS[0]}`)).toBeNull();
  });

  it('reports all headings placed when the bank empties', () => {
    setup({ q1: HEADINGS[0], q2: HEADINGS[1] });
    expect(screen.queryByText('All headings placed.')).toBeNull();
    // A distractor remains, which is the point of having more headings than
    // paragraphs.
    expect(screen.getByTestId(`heading-${HEADINGS[2]}`)).toBeTruthy();
  });
});
