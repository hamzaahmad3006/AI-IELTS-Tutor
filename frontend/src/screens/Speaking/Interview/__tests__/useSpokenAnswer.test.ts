/**
 * Recording an answer and sending it.
 *
 * The cases that matter are the ones that waste a candidate's time or your
 * money: a mis-tap uploaded as an answer, a microphone left open after the
 * screen is gone, an upload failure that loses the recording silently.
 */

import { act, renderHook } from '@testing-library/react-native';
import { PermissionsAndroid, Platform } from 'react-native';
import AudioRecorderPlayer from 'react-native-audio-recorder-player';
import { MIN_ANSWER_MS, useSpokenAnswer } from '../useSpokenAnswer';

interface UploadFile {
  uri: string;
  name: string;
  type: string;
}

const native = AudioRecorderPlayer as unknown as {
  startRecorder: jest.Mock;
  stopRecorder: jest.Mock;
  addRecordBackListener: jest.Mock;
  removeRecordBackListener: jest.Mock;
  __reset: () => void;
};

describe('useSpokenAnswer', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    native.__reset();
    Platform.OS = 'android';
    (PermissionsAndroid.check as jest.Mock) = jest.fn(() =>
      Promise.resolve(true),
    );
  });

  it('records and uploads an answer', async () => {
    // Typed explicitly: an inferred zero-arg mock has no call-args tuple, so
    // the assertion below would not compile.
    const onAnswer = jest.fn(
      (_file: UploadFile): Promise<void> => Promise.resolve(),
    );
    const { result } = renderHook(() => useSpokenAnswer({ onAnswer }));

    await act(async () => {
      await result.current.startRecording();
    });
    expect(result.current.isRecording).toBe(true);

    // Long enough to be a real answer.
    jest.spyOn(Date, 'now').mockReturnValue(Date.now() + 5_000);
    await act(async () => {
      await result.current.stopAndSend();
    });

    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer.mock.calls[0][0]).toEqual(
      expect.objectContaining({ type: 'audio/mp4' }),
    );
    expect(result.current.isRecording).toBe(false);
    (Date.now as jest.Mock).mockRestore();
  });

  it('discards a mis-tap instead of paying to transcribe it', async () => {
    const onAnswer = jest.fn(() => Promise.resolve());
    const { result } = renderHook(() => useSpokenAnswer({ onAnswer }));

    await act(async () => {
      await result.current.startRecording();
      // Stopped immediately: shorter than MIN_ANSWER_MS.
      await result.current.stopAndSend();
    });

    expect(onAnswer).not.toHaveBeenCalled();
    expect(result.current.error).toMatch(/too short/i);
    expect(MIN_ANSWER_MS).toBeGreaterThan(0);
  });

  it('surfaces a blocked microphone with an actionable message', async () => {
    (PermissionsAndroid.check as jest.Mock) = jest.fn(() =>
      Promise.resolve(false),
    );
    (PermissionsAndroid.request as jest.Mock) = jest.fn(() =>
      Promise.resolve(PermissionsAndroid.RESULTS.NEVER_ASK_AGAIN),
    );

    const { result } = renderHook(() =>
      useSpokenAnswer({ onAnswer: jest.fn() }),
    );
    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.isRecording).toBe(false);
    expect(result.current.error).toMatch(/Settings/);
  });

  it('reports an upload failure rather than losing it silently', async () => {
    const onAnswer = jest.fn(() => Promise.reject(new Error('Network Error')));
    const { result } = renderHook(() => useSpokenAnswer({ onAnswer }));

    await act(async () => {
      await result.current.startRecording();
    });
    jest.spyOn(Date, 'now').mockReturnValue(Date.now() + 5_000);
    await act(async () => {
      await result.current.stopAndSend();
    });

    expect(result.current.error).toBe('Network Error');
    expect(result.current.isUploading).toBe(false);
    (Date.now as jest.Mock).mockRestore();
  });

  it('does nothing when stopping without recording', async () => {
    const onAnswer = jest.fn();
    const { result } = renderHook(() => useSpokenAnswer({ onAnswer }));

    await act(async () => {
      await result.current.stopAndSend();
    });

    expect(onAnswer).not.toHaveBeenCalled();
    expect(native.stopRecorder).not.toHaveBeenCalled();
  });

  it('releases the microphone when the screen goes away', async () => {
    const { result, unmount } = renderHook(() =>
      useSpokenAnswer({ onAnswer: jest.fn() }),
    );
    await act(async () => {
      await result.current.startRecording();
    });

    await act(async () => {
      unmount();
    });

    // Leaving it open is a battery drain and, on Android, a recording
    // indicator on a screen the learner has already left.
    expect(native.stopRecorder).toHaveBeenCalled();
    expect(native.removeRecordBackListener).toHaveBeenCalled();
  });

  it('exposes input level so the candidate can see they are heard', async () => {
    const { result } = renderHook(() =>
      useSpokenAnswer({ onAnswer: jest.fn() }),
    );
    await act(async () => {
      await result.current.startRecording();
    });

    const callback = native.addRecordBackListener.mock.calls[0][0];
    await act(async () => {
      callback({ currentMetering: -8 });
    });

    expect(result.current.level).toBe(-8);
  });

  it('discards a recording on request', async () => {
    const onAnswer = jest.fn();
    const { result } = renderHook(() => useSpokenAnswer({ onAnswer }));

    await act(async () => {
      await result.current.startRecording();
      await result.current.discard();
    });

    expect(result.current.isRecording).toBe(false);
    expect(onAnswer).not.toHaveBeenCalled();
  });
});
