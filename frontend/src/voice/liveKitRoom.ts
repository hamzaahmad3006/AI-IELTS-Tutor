/**
 * Joining the examiner's LiveKit room.
 *
 * A thin wrapper over `livekit-client`, written the same way as the recorder:
 * the parts worth getting right are plain functions that can be tested without
 * a device, and the class below is glue over the native SDK.
 *
 * Three things this owns, because each is a real failure the SDK will not stop
 * you from making.
 *
 * **The audio session.** On Android, WebRTC audio only gets hardware echo
 * cancellation if the session is switched into communication mode first.
 * Without it the examiner's own voice comes back through the microphone and is
 * transcribed as the candidate's answer -- the exam scores the examiner.
 *
 * **Cleanup on every path.** A room left connected holds the microphone. The
 * next question then fails to start recording, on a timed exam, with no
 * obvious cause. So disconnect runs from unmount and from failure, not only
 * from the happy path.
 *
 * **Exam state arrives on the data channel** as JSON from a topic the agent
 * publishes to. It is parsed defensively: a malformed frame must not take down
 * an interview that is otherwise fine.
 */

import { AudioSession } from '@livekit/react-native';
import {
  ConnectionState,
  Room,
  RoomEvent,
  Track,
  type RemoteParticipant,
  type RemoteTrack,
} from 'livekit-client';

/** Topic the examiner agent publishes exam state to. Must match the backend. */
export const STATE_TOPIC = 'exam-state';

/** What the agent tells the client about where the exam is. */
export interface ExamState {
  phase?: string;
  part?: number;
  remainingMs?: number;
  isExaminerSpeaking?: boolean;
  transcript?: string;
}

export type RoomStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'disconnected'
  | 'failed';

export class LiveKitError extends Error {}

/**
 * UTF-8 decode, without assuming `TextDecoder` exists.
 *
 * Hermes provides it and `livekit-client` relies on it, so the fast path is
 * almost always taken — but "almost always" is not a good enough basis for
 * the one function that reads exam state, and the fallback is short. It
 * matters for more than tidiness: transcripts are learner text, so a frame
 * can carry any script, and byte-wise decoding would mangle it.
 */
/* eslint-disable no-bitwise -- UTF-8 is defined in terms of bit patterns:
   continuation bytes are masked with 0x3f and shifted six at a time. Writing
   that with arithmetic would be the same operations, spelled less clearly. */
export const decodeUtf8 = (bytes: Uint8Array): string => {
  const Decoder = (
    globalThis as {
      TextDecoder?: new () => { decode(input: Uint8Array): string };
    }
  ).TextDecoder;
  if (Decoder) {
    return new Decoder().decode(bytes);
  }

  let result = '';
  for (let index = 0; index < bytes.length; ) {
    const byte = bytes[index];
    let codePoint: number;
    let width: number;

    if (byte < 0x80) {
      codePoint = byte;
      width = 1;
    } else if ((byte & 0xe0) === 0xc0) {
      codePoint = byte & 0x1f;
      width = 2;
    } else if ((byte & 0xf0) === 0xe0) {
      codePoint = byte & 0x0f;
      width = 3;
    } else {
      codePoint = byte & 0x07;
      width = 4;
    }

    if (index + width > bytes.length) {
      break;
    }
    for (let offset = 1; offset < width; offset += 1) {
      codePoint = (codePoint << 6) | (bytes[index + offset] & 0x3f);
    }
    result += String.fromCodePoint(codePoint);
    index += width;
  }
  return result;
};
/* eslint-enable no-bitwise */

/**
 * Parse a data-channel frame.
 *
 * Returns null rather than throwing on anything unexpected. These arrive from
 * the network mid-exam, and one bad frame must not end a session -- a dropped
 * progress update is invisible, a thrown exception is not.
 */
export const parseExamState = (payload: Uint8Array): ExamState | null => {
  try {
    const parsed: unknown = JSON.parse(decodeUtf8(payload));
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return null;
    }
    return parsed as ExamState;
  } catch {
    return null;
  }
};

/**
 * Map the SDK's connection states onto the four the UI actually distinguishes.
 *
 * Collapsed deliberately: the screen needs to know whether to show the
 * examiner, a spinner, or an error, and mapping each SDK state at every call
 * site is how those drift apart.
 */
export const toRoomStatus = (state: ConnectionState): RoomStatus => {
  switch (state) {
    case ConnectionState.Connecting:
      return 'connecting';
    case ConnectionState.Connected:
      return 'connected';
    case ConnectionState.Reconnecting:
      return 'reconnecting';
    case ConnectionState.Disconnected:
      return 'disconnected';
    default:
      return 'idle';
  }
};

/**
 * Whether a failed connection is worth retrying.
 *
 * A token that has expired or was minted for another room will fail the same
 * way every time; retrying it just delays the error the learner needs to see.
 * A network blip will not.
 */
export const isRetriable = (error: unknown): boolean => {
  const message = (
    error instanceof Error ? error.message : String(error ?? '')
  ).toLowerCase();
  if (
    message.includes('token') ||
    message.includes('unauthorized') ||
    message.includes('401') ||
    message.includes('403') ||
    message.includes('permission')
  ) {
    return false;
  }
  return true;
};

export interface RoomCallbacks {
  onStatus?: (status: RoomStatus) => void;
  onExamState?: (state: ExamState) => void;
  /** The examiner's audio track arriving is what "the exam started" means. */
  onExaminerAudio?: (track: RemoteTrack) => void;
  onError?: (error: Error) => void;
}

/**
 * One interview room at a time.
 */
export class InterviewRoom {
  private room: Room | null = null;
  private callbacks: RoomCallbacks = {};
  private audioSessionStarted = false;

  get status(): RoomStatus {
    return this.room ? toRoomStatus(this.room.state) : 'idle';
  }

  get isConnected(): boolean {
    return this.room?.state === ConnectionState.Connected;
  }

  async connect(
    url: string,
    token: string,
    callbacks: RoomCallbacks = {},
  ): Promise<void> {
    if (this.room) {
      // Refused rather than replaced. Connecting twice leaves the first room
      // holding the microphone, and the symptom is the *next* question failing
      // to record.
      throw new LiveKitError('Already connected to an interview room.');
    }
    this.callbacks = callbacks;

    // Before connecting, not after: the mode has to be set while the session
    // is being configured, or echo cancellation is not applied to the tracks
    // that were already published.
    await AudioSession.startAudioSession();
    this.audioSessionStarted = true;

    const room = new Room({
      // Audio only. Publishing video from an IELTS speaking test would be a
      // surprise to the candidate and a waste of their data.
      adaptiveStream: false,
      dynacast: false,
    });
    this.room = room;

    room
      .on(RoomEvent.ConnectionStateChanged, state => {
        this.callbacks.onStatus?.(toRoomStatus(state));
      })
      .on(
        RoomEvent.DataReceived,
        (payload: Uint8Array, _participant, _kind, topic) => {
          if (topic && topic !== STATE_TOPIC) {
            return;
          }
          const state = parseExamState(payload);
          if (state) {
            this.callbacks.onExamState?.(state);
          }
        },
      )
      .on(
        RoomEvent.TrackSubscribed,
        (track: RemoteTrack, _pub, _participant: RemoteParticipant) => {
          if (track.kind === Track.Kind.Audio) {
            this.callbacks.onExaminerAudio?.(track);
          }
        },
      )
      .on(RoomEvent.Disconnected, () => {
        this.callbacks.onStatus?.('disconnected');
      });

    try {
      await room.connect(url, token);
      // Published after connecting so a failed handshake never opens the
      // microphone at all.
      await room.localParticipant.setMicrophoneEnabled(true);
    } catch (error) {
      // Cleaned up here rather than left to the caller: a half-connected room
      // still holds the audio session.
      await this.disconnect();
      throw new LiveKitError(
        `Could not join the interview: ${(error as Error).message}`,
      );
    }
  }

  /** Mute without leaving. The candidate's own control during the exam. */
  async setMicrophoneEnabled(enabled: boolean): Promise<void> {
    await this.room?.localParticipant.setMicrophoneEnabled(enabled);
  }

  /**
   * Leave and release everything.
   *
   * Never throws: it runs from unmount and from the failure path above, where
   * an exception would mask whatever actually went wrong.
   */
  async disconnect(): Promise<void> {
    const room = this.room;
    this.room = null;
    this.callbacks = {};
    try {
      await room?.disconnect();
    } catch {
      // Already gone. Nothing useful left to do.
    } finally {
      if (this.audioSessionStarted) {
        this.audioSessionStarted = false;
        try {
          await AudioSession.stopAudioSession();
        } catch {
          // Same.
        }
      }
    }
  }
}
