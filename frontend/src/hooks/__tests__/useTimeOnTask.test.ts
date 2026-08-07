/**
 * Time-on-task measurement.
 *
 * The case that matters is backgrounding. Without handling it, every duration
 * is really "time since the screen opened" — so a learner who answers a phone
 * call mid-essay reports two hours of study, confidently and wrongly.
 */

import { act, renderHook } from '@testing-library/react-native';
import { AppState, type AppStateStatus } from 'react-native';
import { useTimeOnTask } from '../useTimeOnTask';

type Handler = (state: AppStateStatus) => void;

let handler: Handler = () => {};

describe('useTimeOnTask', () => {
  let now = 1_000_000;

  beforeEach(() => {
    now = 1_000_000;
    jest.spyOn(Date, 'now').mockImplementation(() => now);
    // spyOn rather than assignment: the module's exports are non-writable, so
    // replacing the function directly throws before any test runs.
    jest
      .spyOn(AppState, 'addEventListener')
      .mockImplementation((_event, fn) => {
        handler = fn as Handler;
        return { remove: jest.fn() } as never;
      });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  const advance = (seconds: number): void => {
    now += seconds * 1000;
  };

  it('counts foreground time', () => {
    const { result } = renderHook(() => useTimeOnTask());
    advance(90);
    expect(result.current.elapsedSeconds()).toBe(90);
  });

  it('stops counting while backgrounded', () => {
    const { result } = renderHook(() => useTimeOnTask());

    advance(30);
    act(() => handler('background' as AppStateStatus));

    // An hour on a phone call is not an hour of study.
    advance(3600);
    expect(result.current.elapsedSeconds()).toBe(30);

    act(() => handler('active' as AppStateStatus));
    advance(20);
    expect(result.current.elapsedSeconds()).toBe(50);
  });

  it('does not lose time when active fires twice', () => {
    const { result } = renderHook(() => useTimeOnTask());
    advance(10);

    // 'active' can fire more than once; resetting the mark each time would
    // discard whatever had accumulated since the last one.
    act(() => handler('active' as AppStateStatus));
    advance(10);
    act(() => handler('active' as AppStateStatus));
    advance(10);

    expect(result.current.elapsedSeconds()).toBe(30);
  });

  it('freezes on finish', () => {
    const { result } = renderHook(() => useTimeOnTask());
    advance(45);

    const total = result.current.finish();
    expect(total).toBe(45);

    advance(600);
    // The screen may stay mounted while the result renders; the clock must not
    // keep running into the reported duration.
    expect(result.current.finish()).toBe(45);
  });

  it('ignores backgrounding after finish', () => {
    const { result } = renderHook(() => useTimeOnTask());
    advance(20);
    result.current.finish();

    act(() => handler('background' as AppStateStatus));
    act(() => handler('active' as AppStateStatus));
    advance(100);

    expect(result.current.finish()).toBe(20);
  });

  it('starts over on reset', () => {
    const { result } = renderHook(() => useTimeOnTask());
    advance(60);
    result.current.finish();

    act(() => result.current.reset());
    advance(15);
    expect(result.current.elapsedSeconds()).toBe(15);
  });
});
