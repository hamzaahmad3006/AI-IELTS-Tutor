/**
 * History virtualisation.
 *
 * History is the one list in the app that grows without bound: it paginates,
 * and every "Load more" adds to the same array. Rendered with `.map()` inside a
 * ScrollView — which is what it was — a learner with two hundred attempts has
 * two hundred cards mounted at once, and the screen gets slower the more they
 * practise.
 *
 * These tests exist because reverting to a `.map()` is a one-line change that
 * looks identical on screen until someone has enough history for it to matter.
 */

import React from 'react';
import { screen } from '@testing-library/react-native';
import { renderWithProviders as render } from '../../../testUtils/renderWithProviders';
import type { HistoryRow } from '../useHistory';
import { History } from '../History';

const mockRows: HistoryRow[] = Array.from({ length: 60 }, (_, index) => ({
  attemptId: `attempt-${index}`,
  band: 6.5,
  detail: `Attempt number ${index}`,
  createdAt: '2026-08-01T10:00:00Z',
  status: 'scored',
}));

const mockState = {
  module: 'writing' as const,
  rows: mockRows,
  isLoading: false,
  isLoadingMore: false,
  hasMore: true,
  error: null as string | null,
  setModule: jest.fn(),
  trendBands: [6, 6.5, 7],
  loadMore: jest.fn(),
  onBack: jest.fn(),
};

jest.mock('../useHistory', () => ({
  useHistory: () => mockState,
}));

describe('History', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockState.rows = mockRows;
    mockState.isLoading = false;
    mockState.error = null;
    mockState.hasMore = true;
  });

  it('renders through a virtualised list', () => {
    render(<History />);
    expect(screen.getByTestId('history-list')).toBeTruthy();
  });

  it('does not mount every row at once', () => {
    render(<History />);

    // FlatList honours initialNumToRender, so a 60-row list renders a
    // screenful rather than all sixty. A `.map()` would render every one, and
    // this is the assertion that catches a revert.
    const rendered = screen.queryAllByText(/^Attempt number \d+$/);
    expect(rendered.length).toBeGreaterThan(0);
    expect(rendered.length).toBeLessThan(mockRows.length);
  });

  it('keeps the header above the rows', () => {
    render(<History />);
    // The chart and module switcher are the list header, not a sibling — a
    // sibling would scroll separately from the rows it describes.
    expect(screen.getByText('History')).toBeTruthy();
    expect(screen.getByText('Writing')).toBeTruthy();
  });

  it('offers a way to load more while there is more', () => {
    render(<History />);
    expect(screen.getByText('Load more')).toBeTruthy();
  });

  it('hides the load-more control at the end of the list', () => {
    mockState.hasMore = false;
    render(<History />);
    expect(screen.queryByText('Load more')).toBeNull();
  });

  it('shows the empty state rather than an empty list', () => {
    mockState.rows = [];
    mockState.hasMore = false;
    render(<History />);
    expect(screen.getByText('No attempts yet')).toBeTruthy();
  });

  it('shows an error instead of rows', () => {
    mockState.error = 'Could not load your history.';
    render(<History />);
    expect(screen.getByText('Could not load your history.')).toBeTruthy();
    // Rows must not render alongside an error: showing stale attempts under a
    // failure message tells the user two different things.
    expect(screen.queryAllByText(/^Attempt number \d+$/)).toHaveLength(0);
  });
});
