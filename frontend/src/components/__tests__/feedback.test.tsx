/**
 * Global feedback surfaces: toast queue, empty/error states, skeletons and the
 * crash boundary.
 */

import React from 'react';
import { Text } from 'react-native';
import { act, screen } from '@testing-library/react-native';
import { renderWithProviders as render } from '../../testUtils/renderWithProviders';
import { EmptyState } from '../EmptyState/EmptyState';
import { ErrorBoundary } from '../ErrorBoundary/ErrorBoundary';
import { Skeleton, SkeletonCard } from '../Skeleton/Skeleton';
import { ToastHost } from '../Toast/ToastHost';
import { store } from '@redux/store';
import { clearToasts, dismissToast, showToast } from '@redux/slices/toastSlice';

describe('toastSlice', () => {
  beforeEach(() => {
    store.dispatch(clearToasts());
  });

  it('queues a toast with a tone-appropriate duration', () => {
    store.dispatch(showToast({ message: 'Saved', tone: 'success' }));
    const [toast] = store.getState().toast.queue;
    expect(toast.message).toBe('Saved');
    expect(toast.tone).toBe('success');
    // Errors linger longer than confirmations.
    store.dispatch(showToast({ message: 'Broke', tone: 'error' }));
    const error = store.getState().toast.queue[1];
    expect(error.durationMs).toBeGreaterThan(toast.durationMs);
  });

  it('collapses duplicate messages instead of stacking them', () => {
    // A screen retrying three times must not produce three identical bars.
    store.dispatch(showToast({ message: 'Offline' }));
    store.dispatch(showToast({ message: 'Offline' }));
    store.dispatch(showToast({ message: 'Offline' }));
    expect(store.getState().toast.queue).toHaveLength(1);
  });

  it('dismisses by id', () => {
    store.dispatch(showToast({ message: 'One' }));
    store.dispatch(showToast({ message: 'Two' }));
    const [first] = store.getState().toast.queue;
    store.dispatch(dismissToast(first.id));
    expect(store.getState().toast.queue.map(t => t.message)).toEqual(['Two']);
  });
});

describe('ToastHost', () => {
  beforeEach(() => {
    store.dispatch(clearToasts());
  });

  it('renders nothing when the queue is empty', () => {
    render(<ToastHost />);
    expect(screen.queryByTestId('toast-host')).toBeNull();
  });

  it('shows only the front of the queue', () => {
    store.dispatch(showToast({ message: 'First up', tone: 'error' }));
    store.dispatch(showToast({ message: 'Waiting', tone: 'info' }));
    render(<ToastHost />);
    expect(screen.getByText('First up')).toBeTruthy();
    expect(screen.queryByText('Waiting')).toBeNull();
    expect(screen.getByTestId('toast-error')).toBeTruthy();
  });

  it('auto-dismisses after its duration', () => {
    jest.useFakeTimers();
    try {
      store.dispatch(
        showToast({ message: 'Transient', tone: 'info', durationMs: 1000 }),
      );
      render(<ToastHost />);
      expect(screen.getByText('Transient')).toBeTruthy();
      act(() => {
        jest.advanceTimersByTime(1000);
      });
      expect(store.getState().toast.queue).toHaveLength(0);
    } finally {
      jest.useRealTimers();
    }
  });
});

describe('EmptyState', () => {
  it('offers a retry in the error variant', () => {
    const onAction = jest.fn();
    render(
      <EmptyState
        variant="error"
        title="Could not load"
        message="Try again in a moment."
        actionLabel="Retry"
        onAction={onAction}
      />,
    );
    expect(screen.getByTestId('empty-state-error')).toBeTruthy();
    expect(screen.getByText('Could not load')).toBeTruthy();
    expect(screen.getByText('Retry')).toBeTruthy();
  });

  it('omits the action when there is nothing to retry', () => {
    // A brand-new account is not an error and must not be dressed up as one.
    render(<EmptyState title="No practice yet" />);
    expect(screen.getByTestId('empty-state-empty')).toBeTruthy();
    expect(screen.queryByText('Retry')).toBeNull();
  });

  it('distinguishes offline from a generic failure', () => {
    render(<EmptyState variant="offline" title="You are offline" />);
    expect(screen.getByTestId('empty-state-offline')).toBeTruthy();
  });
});

describe('Skeleton', () => {
  it('exposes itself to assistive tech as loading', () => {
    render(<Skeleton testID="bar" />);
    const bar = screen.getByTestId('bar');
    expect(bar.props.accessibilityLabel).toBe('Loading');
  });

  it('renders a title plus the requested body lines', () => {
    render(<SkeletonCard lines={4} />);
    expect(screen.getByTestId('skeleton-card')).toBeTruthy();
    expect(screen.getAllByLabelText('Loading')).toHaveLength(5); // title + 4
  });
});

describe('ErrorBoundary', () => {
  const Boom: React.FC = () => {
    throw new Error('render exploded');
  };

  it('passes children through when nothing throws', () => {
    render(
      <ErrorBoundary>
        <Text>All good</Text>
      </ErrorBoundary>,
    );
    expect(screen.getByText('All good')).toBeTruthy();
  });

  it('shows a recoverable fallback instead of a blank screen', () => {
    // React logs the caught error; silence it so the run stays readable.
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    const onError = jest.fn();
    try {
      render(
        <ErrorBoundary onError={onError}>
          <Boom />
        </ErrorBoundary>,
      );
      expect(screen.getByTestId('error-boundary-fallback')).toBeTruthy();
      expect(screen.getByText('Something broke')).toBeTruthy();
      expect(screen.getByText('Try again')).toBeTruthy();
      expect(onError).toHaveBeenCalled();
    } finally {
      spy.mockRestore();
    }
  });
});
