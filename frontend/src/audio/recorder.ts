/**
 * Microphone recording for the spoken interview.
 *
 * A thin wrapper over the native recorder, with the parts worth getting right
 * kept in plain functions so they can be tested without a device.
 *
 * The lifecycle is the fragile bit. A recorder that is started twice, or
 * stopped when it was never started, throws from native code — and on a timed
 * exam that surfaces as the whole question being lost. So state is tracked here
 * and the illegal transitions are refused locally rather than sent down to
 * crash.
 *
 * Permissions are asked for at the moment of first use rather than on app
 * start. A microphone prompt that appears before the learner has done anything
 * reads as an app that wants to listen to them; one that appears when they tap
 * "answer" reads as the feature working.
 */

import { PermissionsAndroid, Platform } from 'react-native';
import AudioRecorderPlayer from 'react-native-audio-recorder-player';
import { t } from '../i18n';

/** Android's recorder produces AAC in an MP4 container. */
export const RECORDING_MIME_TYPE = 'audio/mp4';
export const RECORDING_EXTENSION = 'm4a';

/**
 * Refused above this before upload. The backend caps at 10 MB; failing here
 * gives a message about the recording instead of a rejected request, and saves
 * pushing megabytes over a phone connection to be told no.
 */
export const MAX_RECORDING_BYTES = 10 * 1024 * 1024;

export type PermissionResult = 'granted' | 'denied' | 'blocked';

export interface Recording {
  uri: string;
  name: string;
  type: string;
  durationMs: number;
}

export class RecorderError extends Error {}

/**
 * Ask for the microphone.
 *
 * `blocked` is separated from `denied` on purpose: a denial can be re-asked,
 * but "never ask again" cannot, and the only useful response to it is to send
 * the learner to system settings. Telling them to "allow the prompt" when no
 * prompt will ever appear again is the kind of dead end that gets an app
 * uninstalled.
 */
export const requestMicrophonePermission =
  async (): Promise<PermissionResult> => {
    if (Platform.OS !== 'android') {
      return 'granted';
    }

    const permission = PermissionsAndroid.PERMISSIONS.RECORD_AUDIO;

    if (await PermissionsAndroid.check(permission)) {
      return 'granted';
    }

    const result = await PermissionsAndroid.request(permission, {
      title: 'Microphone access',
      message:
        'The speaking test needs your microphone to record your answers.',
      buttonPositive: 'Allow',
      buttonNegative: 'Not now',
    });

    if (result === PermissionsAndroid.RESULTS.GRANTED) {
      return 'granted';
    }
    if (result === PermissionsAndroid.RESULTS.NEVER_ASK_AGAIN) {
      return 'blocked';
    }
    return 'denied';
  };

/** Build the multipart file descriptor the upload endpoint expects. */
export const toUploadFile = (uri: string, durationMs: number): Recording => ({
  // Android returns a bare path from some recorder versions; the fetch layer
  // needs a URI scheme or the upload silently sends nothing.
  uri: uri.startsWith('file://') ? uri : `file://${uri}`,
  name: `answer-${Date.now()}.${RECORDING_EXTENSION}`,
  type: RECORDING_MIME_TYPE,
  durationMs,
});

type RecorderState = 'idle' | 'recording';

/**
 * One recording at a time, with the illegal transitions refused locally.
 */
export class InterviewRecorder {
  private state: RecorderState = 'idle';
  private startedAt = 0;
  private onLevel?: (metering: number) => void;

  get isRecording(): boolean {
    return this.state === 'recording';
  }

  /** Subscribe to input level, for a waveform or a "we can hear you" cue. */
  setLevelListener(listener?: (metering: number) => void): void {
    this.onLevel = listener;
  }

  async start(): Promise<void> {
    if (this.state === 'recording') {
      // Refused rather than restarted. Restarting would discard whatever the
      // candidate had already said, which is worse than ignoring a double tap.
      return;
    }

    const permission = await requestMicrophonePermission();
    if (permission !== 'granted') {
      throw new RecorderError(
        permission === 'blocked'
          ? t('error.microphoneBlocked')
          : t('error.microphoneNeeded'),
      );
    }

    AudioRecorderPlayer.addRecordBackListener(meta => {
      this.onLevel?.(meta.currentMetering ?? 0);
    });

    try {
      // Metering on: it drives the level indicator, and without a visible cue
      // a candidate cannot tell whether they are being heard.
      await AudioRecorderPlayer.startRecorder(undefined, undefined, true);
    } catch (error) {
      AudioRecorderPlayer.removeRecordBackListener();
      throw new RecorderError(
        `Could not start recording: ${(error as Error).message}`,
      );
    }

    this.state = 'recording';
    this.startedAt = Date.now();
  }

  async stop(): Promise<Recording> {
    if (this.state !== 'recording') {
      throw new RecorderError('Nothing is being recorded.');
    }

    // Cleared before awaiting: if the native stop throws, the recorder must
    // not be left believing it is still running, or every later attempt fails.
    this.state = 'idle';
    const durationMs = Date.now() - this.startedAt;

    try {
      const uri = await AudioRecorderPlayer.stopRecorder();
      return toUploadFile(uri, durationMs);
    } finally {
      AudioRecorderPlayer.removeRecordBackListener();
    }
  }

  /**
   * Stop and discard. Used when a screen unmounts mid-answer.
   *
   * Never throws: it runs from cleanup paths, where an exception would mask
   * whatever caused the teardown in the first place.
   */
  async cancel(): Promise<void> {
    if (this.state !== 'recording') {
      return;
    }
    this.state = 'idle';
    try {
      await AudioRecorderPlayer.stopRecorder();
    } catch {
      // Already stopped, or the native side is gone. Either way there is
      // nothing useful left to do.
    } finally {
      AudioRecorderPlayer.removeRecordBackListener();
    }
  }
}
