/**
 * The interview recorder.
 *
 * The assertions are mostly about lifecycle and permissions, because that is
 * where this fails in ways a candidate feels: a double tap that discards their
 * half-finished answer, a stop that leaves the recorder wedged, or a permission
 * dead end with no way out.
 */

import { PermissionsAndroid, Platform } from 'react-native';
import AudioRecorderPlayer from 'react-native-audio-recorder-player';
import {
  InterviewRecorder,
  RECORDING_MIME_TYPE,
  RecorderError,
  requestMicrophonePermission,
  toUploadFile,
  meteringToPercent,
  SILENCE_DB,
} from '../recorder';

const native = AudioRecorderPlayer as unknown as {
  startRecorder: jest.Mock;
  stopRecorder: jest.Mock;
  addRecordBackListener: jest.Mock;
  removeRecordBackListener: jest.Mock;
  __reset: () => void;
};

const grant = (): void => {
  (PermissionsAndroid.check as jest.Mock) = jest.fn(() =>
    Promise.resolve(true),
  );
};

describe('requestMicrophonePermission', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Platform.OS = 'android';
  });

  it('does not re-prompt when already granted', async () => {
    (PermissionsAndroid.check as jest.Mock) = jest.fn(() =>
      Promise.resolve(true),
    );
    (PermissionsAndroid.request as jest.Mock) = jest.fn();

    await expect(requestMicrophonePermission()).resolves.toBe('granted');
    expect(PermissionsAndroid.request).not.toHaveBeenCalled();
  });

  it('prompts when not yet granted', async () => {
    (PermissionsAndroid.check as jest.Mock) = jest.fn(() =>
      Promise.resolve(false),
    );
    (PermissionsAndroid.request as jest.Mock) = jest.fn(() =>
      Promise.resolve(PermissionsAndroid.RESULTS.GRANTED),
    );

    await expect(requestMicrophonePermission()).resolves.toBe('granted');
    expect(PermissionsAndroid.request).toHaveBeenCalled();
  });

  it('separates a refusal from "never ask again"', async () => {
    (PermissionsAndroid.check as jest.Mock) = jest.fn(() =>
      Promise.resolve(false),
    );

    (PermissionsAndroid.request as jest.Mock) = jest.fn(() =>
      Promise.resolve(PermissionsAndroid.RESULTS.DENIED),
    );
    await expect(requestMicrophonePermission()).resolves.toBe('denied');

    // The distinction matters: a denial can be re-asked, "never ask again"
    // cannot, and telling someone to allow a prompt that will never appear
    // again is a dead end.
    (PermissionsAndroid.request as jest.Mock) = jest.fn(() =>
      Promise.resolve(PermissionsAndroid.RESULTS.NEVER_ASK_AGAIN),
    );
    await expect(requestMicrophonePermission()).resolves.toBe('blocked');
  });
});

describe('toUploadFile', () => {
  it('adds the file scheme when the recorder omits it', () => {
    // Some recorder versions return a bare path, and the fetch layer then
    // uploads nothing at all -- silently, which is the worst part.
    const file = toUploadFile('/data/user/0/app/cache/sound.m4a', 4000);
    expect(file.uri).toBe('file:///data/user/0/app/cache/sound.m4a');
  });

  it('leaves an existing scheme alone', () => {
    const file = toUploadFile('file:///tmp/a.m4a', 1000);
    expect(file.uri).toBe('file:///tmp/a.m4a');
  });

  it('describes itself for the multipart upload', () => {
    const file = toUploadFile('/tmp/a.m4a', 2500);
    expect(file.type).toBe(RECORDING_MIME_TYPE);
    expect(file.name).toMatch(/\.m4a$/);
    expect(file.durationMs).toBe(2500);
  });
});

describe('InterviewRecorder', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    native.__reset();
    Platform.OS = 'android';
    grant();
  });

  it('records and returns an uploadable file', async () => {
    const recorder = new InterviewRecorder();
    await recorder.start();
    expect(recorder.isRecording).toBe(true);

    const file = await recorder.stop();
    expect(recorder.isRecording).toBe(false);
    expect(file.uri).toContain('file://');
    expect(file.durationMs).toBeGreaterThanOrEqual(0);
  });

  it('ignores a second start instead of discarding the answer', async () => {
    const recorder = new InterviewRecorder();
    await recorder.start();
    await recorder.start();

    // Restarting would throw away whatever the candidate had already said,
    // which is worse than ignoring a double tap.
    expect(native.startRecorder).toHaveBeenCalledTimes(1);
    expect(recorder.isRecording).toBe(true);
  });

  it('refuses to stop when nothing is recording', async () => {
    const recorder = new InterviewRecorder();
    await expect(recorder.stop()).rejects.toBeInstanceOf(RecorderError);
    expect(native.stopRecorder).not.toHaveBeenCalled();
  });

  it('does not wedge when the native stop throws', async () => {
    const recorder = new InterviewRecorder();
    await recorder.start();
    native.stopRecorder.mockRejectedValueOnce(new Error('native exploded'));

    await expect(recorder.stop()).rejects.toThrow('native exploded');

    // State is cleared before awaiting, so a failed stop does not leave the
    // recorder believing it is still running and failing every later attempt.
    expect(recorder.isRecording).toBe(false);
    await expect(recorder.start()).resolves.toBeUndefined();
  });

  it('always removes its listener', async () => {
    const recorder = new InterviewRecorder();
    await recorder.start();
    await recorder.stop();
    expect(native.removeRecordBackListener).toHaveBeenCalled();
  });

  it('fails with an actionable message when permission is refused', async () => {
    (PermissionsAndroid.check as jest.Mock) = jest.fn(() =>
      Promise.resolve(false),
    );
    (PermissionsAndroid.request as jest.Mock) = jest.fn(() =>
      Promise.resolve(PermissionsAndroid.RESULTS.NEVER_ASK_AGAIN),
    );

    const recorder = new InterviewRecorder();
    await expect(recorder.start()).rejects.toThrow(/Settings/);
    expect(native.startRecorder).not.toHaveBeenCalled();
  });

  it('cancel never throws, even from a teardown path', async () => {
    const recorder = new InterviewRecorder();
    await recorder.start();
    native.stopRecorder.mockRejectedValueOnce(new Error('gone'));

    // Runs from cleanup, where an exception would mask whatever caused the
    // teardown in the first place.
    await expect(recorder.cancel()).resolves.toBeUndefined();
    expect(recorder.isRecording).toBe(false);
  });

  it('cancel on an idle recorder is a no-op', async () => {
    const recorder = new InterviewRecorder();
    await expect(recorder.cancel()).resolves.toBeUndefined();
    expect(native.stopRecorder).not.toHaveBeenCalled();
  });

  it('reports input level so the candidate can see they are heard', async () => {
    const levels: number[] = [];
    const recorder = new InterviewRecorder();
    recorder.setLevelListener(level => levels.push(level));
    await recorder.start();

    const callback = native.addRecordBackListener.mock.calls[0][0];
    callback({ currentMetering: -12 });
    callback({});

    // Percentages, not raw dBFS: -12 dBFS is loud, and a missing reading is
    // treated as silence rather than as maximum.
    expect(levels).toEqual([meteringToPercent(-12), 0]);
    expect(levels[0]).toBe(80);
  });
});

describe('meteringToPercent', () => {
  it('maps dBFS onto the bar, not straight through', () => {
    // The bug this replaced: currentMetering is negative, and the screen
    // rendered Math.max(4, level) as a percentage — so the bar sat at 4%
    // no matter how loud the candidate was. A "we can hear you" cue that
    // cannot move tells them the microphone is dead.
    expect(meteringToPercent(0)).toBe(100);
    expect(meteringToPercent(SILENCE_DB)).toBe(0);
    expect(meteringToPercent(-30)).toBe(50);
    // Ambient room noise measured on a real device during QA.
    expect(meteringToPercent(-31)).toBeGreaterThan(40);
    expect(meteringToPercent(-35)).toBeGreaterThan(30);
  });

  it('clamps the extremes Android actually reports', () => {
    // Android bottoms out near -160, and the meter occasionally emits 0/NaN
    // between frames.
    expect(meteringToPercent(-160)).toBe(0);
    expect(meteringToPercent(10)).toBe(100);
    expect(meteringToPercent(NaN)).toBe(0);
    expect(meteringToPercent(-Infinity)).toBe(0);
  });
});
