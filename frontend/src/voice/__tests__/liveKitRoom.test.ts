/**
 * The interview room wrapper.
 *
 * WebRTC cannot run here, so what is covered is everything the wrapper decides
 * *around* it -- and that is where the failures a candidate would notice live:
 * a second connect leaving the first room holding the microphone, a failed
 * handshake leaking the audio session, a malformed data frame ending an
 * otherwise healthy exam.
 */

import { AudioSession } from '@livekit/react-native';
import { ConnectionState, Room, RoomEvent, Track } from 'livekit-client';
import {
  InterviewRoom,
  LiveKitError,
  STATE_TOPIC,
  decodeUtf8,
  isRetriable,
  parseExamState,
  toRoomStatus,
} from '../liveKitRoom';

const FakeRoom = Room as unknown as {
  last: any;
  failNextConnect: boolean;
  failureMessage: string;
};

const { TextEncoder: PlatformEncoder } = globalThis as unknown as {
  TextEncoder: new () => { encode(input: string): Uint8Array };
};

const encode = (value: unknown): Uint8Array => {
  const text = typeof value === 'string' ? value : JSON.stringify(value);
  // Captured once at module load, before any test deletes TextDecoder, so
  // encoding stays available while the decoder fallback is being exercised.
  return new PlatformEncoder().encode(text);
};

beforeEach(() => {
  jest.clearAllMocks();
  FakeRoom.failNextConnect = false;
  FakeRoom.failureMessage = 'network unreachable';
  FakeRoom.last = null;
});

describe('parseExamState', () => {
  it('reads a state frame', () => {
    expect(
      parseExamState(encode({ phase: 'part2', remainingMs: 90000 })),
    ).toEqual({ phase: 'part2', remainingMs: 90000 });
  });

  it('returns null for anything malformed rather than throwing', () => {
    // These arrive from the network mid-exam. One bad frame must not end a
    // session: a dropped progress update is invisible, an exception is not.
    expect(parseExamState(encode('not json at all'))).toBeNull();
    expect(parseExamState(new Uint8Array([0xff, 0xfe, 0x00]))).toBeNull();
    expect(parseExamState(encode([1, 2, 3]))).toBeNull();
    expect(parseExamState(encode(null))).toBeNull();
    expect(parseExamState(encode(42))).toBeNull();
    expect(parseExamState(new Uint8Array())).toBeNull();
  });
});

describe('decodeUtf8', () => {
  const cases = [
    'plain ascii',
    'café, naïve, £20',
    'مرحبا بالعالم',
    '日本語のテキスト',
    'emoji 🎧 in a transcript',
  ];

  it('matches the platform decoder', () => {
    for (const text of cases) {
      expect(decodeUtf8(encode(text))).toBe(text);
    }
  });

  it('decodes without TextDecoder, for runtimes that lack it', () => {
    // Transcripts are learner text and can be in any script, so the fallback
    // has to be a real UTF-8 decoder rather than a byte-wise cast.
    const original = (globalThis as Record<string, unknown>).TextDecoder;
    delete (globalThis as Record<string, unknown>).TextDecoder;
    try {
      for (const text of cases) {
        expect(decodeUtf8(encode(text))).toBe(text);
      }
      expect(decodeUtf8(new Uint8Array())).toBe('');
    } finally {
      (globalThis as Record<string, unknown>).TextDecoder = original;
    }
  });
});

describe('toRoomStatus', () => {
  it('collapses the SDK states to the ones the UI distinguishes', () => {
    expect(toRoomStatus(ConnectionState.Connecting)).toBe('connecting');
    expect(toRoomStatus(ConnectionState.Connected)).toBe('connected');
    expect(toRoomStatus(ConnectionState.Reconnecting)).toBe('reconnecting');
    expect(toRoomStatus(ConnectionState.Disconnected)).toBe('disconnected');
    expect(toRoomStatus('something-new' as ConnectionState)).toBe('idle');
  });
});

describe('isRetriable', () => {
  it('does not retry a credential failure', () => {
    // An expired or mis-scoped token fails identically every time; retrying
    // only delays the error the learner needs to see.
    for (const message of [
      'invalid token',
      'Unauthorized',
      'server responded with 401',
      '403 forbidden',
      'permission denied',
    ]) {
      expect(isRetriable(new Error(message))).toBe(false);
    }
  });

  it('retries a transport failure', () => {
    expect(isRetriable(new Error('network unreachable'))).toBe(true);
    expect(isRetriable(new Error('ICE connection failed'))).toBe(true);
    expect(isRetriable(undefined)).toBe(true);
  });
});

describe('InterviewRoom', () => {
  it('starts the audio session before connecting', async () => {
    const room = new InterviewRoom();
    await room.connect('wss://lk.test', 'token-abc');

    // Ordering is the assertion. Echo cancellation is applied when the session
    // is configured, so a session started after connect leaves the already
    // published track without it -- and the examiner's voice is transcribed as
    // the candidate's answer.
    expect(AudioSession.startAudioSession).toHaveBeenCalled();
    const sessionOrder = (AudioSession.startAudioSession as jest.Mock).mock
      .invocationCallOrder[0];
    const connectOrder = FakeRoom.last.connect.mock.invocationCallOrder[0];
    expect(sessionOrder).toBeLessThan(connectOrder);

    expect(room.isConnected).toBe(true);
    await room.disconnect();
  });

  it('publishes the microphone only after the handshake succeeds', async () => {
    const room = new InterviewRoom();
    await room.connect('wss://lk.test', 'token-abc');

    const participant = FakeRoom.last.localParticipant;
    expect(participant.setMicrophoneEnabled).toHaveBeenCalledWith(true);
    expect(
      participant.setMicrophoneEnabled.mock.invocationCallOrder[0],
    ).toBeGreaterThan(FakeRoom.last.connect.mock.invocationCallOrder[0]);

    await room.disconnect();
  });

  it('refuses a second connect instead of replacing the room', async () => {
    const room = new InterviewRoom();
    await room.connect('wss://lk.test', 'token-abc');

    // Replacing would leave the first room holding the microphone, and the
    // symptom is the *next* question failing to record.
    await expect(room.connect('wss://lk.test', 'token-abc')).rejects.toThrow(
      LiveKitError,
    );
    await room.disconnect();
  });

  it('releases the audio session when the handshake fails', async () => {
    FakeRoom.failNextConnect = true;
    const room = new InterviewRoom();

    await expect(room.connect('wss://lk.test', 'bad')).rejects.toThrow(
      LiveKitError,
    );

    // A half-connected room still holds the session; leaving that to the
    // caller is how a device ends up with a dead microphone.
    expect(AudioSession.stopAudioSession).toHaveBeenCalled();
    expect(room.isConnected).toBe(false);
    // And the wrapper is reusable afterwards rather than permanently poisoned.
    await expect(
      room.connect('wss://lk.test', 'good'),
    ).resolves.toBeUndefined();
    await room.disconnect();
  });

  it('routes exam state from the agent topic and ignores others', async () => {
    const states: unknown[] = [];
    const room = new InterviewRoom();
    await room.connect('wss://lk.test', 'token-abc', {
      onExamState: state => states.push(state),
    });

    FakeRoom.last.emit(
      RoomEvent.DataReceived,
      encode({ phase: 'part1' }),
      null,
      null,
      STATE_TOPIC,
    );
    // Another topic on the same channel is not ours.
    FakeRoom.last.emit(
      RoomEvent.DataReceived,
      encode({ phase: 'nope' }),
      null,
      null,
      'chat',
    );
    // A malformed frame is dropped, not thrown.
    FakeRoom.last.emit(
      RoomEvent.DataReceived,
      encode('garbage'),
      null,
      null,
      STATE_TOPIC,
    );

    expect(states).toEqual([{ phase: 'part1' }]);
    await room.disconnect();
  });

  it('surfaces the examiner audio track and not other kinds', async () => {
    const tracks: unknown[] = [];
    const room = new InterviewRoom();
    await room.connect('wss://lk.test', 'token-abc', {
      onExaminerAudio: track => tracks.push(track),
    });

    FakeRoom.last.emit(
      RoomEvent.TrackSubscribed,
      { kind: Track.Kind.Audio, sid: 'a1' },
      null,
      null,
    );
    FakeRoom.last.emit(
      RoomEvent.TrackSubscribed,
      { kind: Track.Kind.Video, sid: 'v1' },
      null,
      null,
    );

    expect(tracks).toHaveLength(1);
    expect((tracks[0] as { sid: string }).sid).toBe('a1');
    await room.disconnect();
  });

  it('reports status changes', async () => {
    const seen: string[] = [];
    const room = new InterviewRoom();
    await room.connect('wss://lk.test', 'token-abc', {
      onStatus: status => seen.push(status),
    });

    FakeRoom.last.emit(
      RoomEvent.ConnectionStateChanged,
      ConnectionState.Reconnecting,
    );
    expect(seen).toContain('connected');
    expect(seen).toContain('reconnecting');
    await room.disconnect();
  });

  it('disconnects idempotently and never throws', async () => {
    const room = new InterviewRoom();
    await room.connect('wss://lk.test', 'token-abc');

    FakeRoom.last.disconnect.mockRejectedValueOnce(new Error('already gone'));

    // Runs from unmount and from the failure path, where an exception would
    // mask whatever actually went wrong.
    await expect(room.disconnect()).resolves.toBeUndefined();
    await expect(room.disconnect()).resolves.toBeUndefined();
    expect(room.status).toBe('idle');
  });

  it('mutes without leaving the room', async () => {
    const room = new InterviewRoom();
    await room.connect('wss://lk.test', 'token-abc');

    await room.setMicrophoneEnabled(false);
    expect(FakeRoom.last.localParticipant.micEnabled).toBe(false);
    expect(room.isConnected).toBe(true);

    await room.disconnect();
    // Safe after disconnect rather than a null dereference from a late tap.
    await expect(room.setMicrophoneEnabled(true)).resolves.toBeUndefined();
  });
});
