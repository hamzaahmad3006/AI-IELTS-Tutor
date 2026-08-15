/**
 * State-frame mapping for the live interview screen.
 *
 * This is the whole of what the candidate sees during a spoken interview: an
 * orb, a colour and one line of text, driven entirely by frames the examiner
 * worker publishes. Get it wrong and the room still connects, the audio still
 * plays, and the screen just says the wrong thing — which on a recorded demo
 * is the part people notice.
 */

import { phaseFor, type Phase } from '../useLiveInterview';

describe('phaseFor', () => {
  it('maps each state the worker publishes', () => {
    expect(phaseFor({ speaking: true }, 'listening')).toBe('examinerSpeaking');
    expect(phaseFor({ listening: true }, 'thinking')).toBe('listening');
    expect(phaseFor({ thinking: true }, 'listening')).toBe('thinking');
    expect(phaseFor({ finished: true }, 'listening')).toBe('finished');
  });

  it('treats finished as final, whatever else the frame claims', () => {
    // The closing turn arrives as speaking+finished together. Ending the
    // interview is the fact worth rendering; "examiner is speaking" leaves the
    // screen mid-interview forever.
    expect(phaseFor({ finished: true, speaking: true }, 'listening')).toBe(
      'finished',
    );
  });

  it('holds the current phase on an empty frame', () => {
    // One of these arrives at the end of every examiner turn -- speaking goes
    // false and nothing replaces it. Falling back to a default would flicker
    // the screen between every single question.
    expect(phaseFor({}, 'listening')).toBe('listening');
    expect(phaseFor({}, 'examinerSpeaking')).toBe('examinerSpeaking');
    expect(phaseFor({ speaking: false }, 'thinking')).toBe('thinking');
  });

  it('leaves connecting only once a real frame arrives', () => {
    // The first frame means the worker is there. Before that the screen must
    // keep saying "connecting", because nothing has been heard yet.
    expect(phaseFor({}, 'connecting')).toBe('waiting');
    expect(phaseFor({ speaking: true }, 'connecting')).toBe('examinerSpeaking');
  });

  it('never leaves a terminal phase on a stray frame', () => {
    // Frames can arrive after the interview ends, as the worker tears down.
    // They must not resurrect a finished screen.
    const terminal: Phase[] = ['finished'];
    for (const phase of terminal) {
      expect(phaseFor({}, phase)).toBe(phase);
    }
  });
});
