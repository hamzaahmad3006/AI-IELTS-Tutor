/**
 * English strings.
 *
 * Keys are `area.thing`, flat rather than nested, because a flat map is what
 * makes a missing key visible on screen as `area.thing` instead of resolving
 * to an empty object and rendering nothing.
 *
 * IELTS terminology stays in English in every locale — "band", "Task 1", "cue
 * card" are the words printed on the real exam paper wherever it is sat, and
 * translating them would teach a learner vocabulary the examiner will not use.
 */

export const en = {
  // Accessibility labels. These are read aloud rather than shown, so they are
  // written as a sentence a person would say, not as a UI label: "Start
  // recording your answer", not "Record".
  'a11y.record.start': 'Start recording your answer',
  'a11y.record.stop': 'Stop recording and send your answer',
  'a11y.record.uploading': 'Sending your answer',
  'a11y.back': 'Go back',
  'a11y.close': 'Close',
  'a11y.band': 'Estimated band {band} out of 9',
  'a11y.progress': '{done} of {total} complete',
  'a11y.timer': '{seconds} seconds remaining',
  'a11y.playAudio': 'Play the audio clip',
  'a11y.pauseAudio': 'Pause the audio clip',

  // Recording a practice answer.
  'speaking.nothingHeard':
    'We could not hear anything in that recording. Try again, or type your answer below.',
  'speaking.transcribeFailed':
    'That recording could not be transcribed. You can try again or type your answer.',
  'speaking.recording': 'Recording — tap when you have finished',
  'speaking.tapToRecord': 'Record your answer',
  'speaking.transcribing': 'Writing down what you said…',

  // The spoken interview.
  'interview.preparing': 'Preparing your speaking test…',
  'interview.ready': "I'm ready",
  'interview.startEarly': 'Start speaking now',
  'interview.prepHint': 'Make notes if you like. You can start early.',
  'interview.tapToAnswer': 'Tap to answer',
  'interview.listening': 'Listening — tap when you have finished',
  'interview.sending': 'Sending your answer…',
  'interview.complete': 'Speaking test complete',
  'interview.youShouldSay': 'You should say:',
  'interview.retry': 'Try again',

  'interview.phase.greeting': 'Introduction',
  'interview.phase.part1': 'Part 1 · Interview',
  'interview.phase.part2_cue': 'Part 2 · Task card',
  'interview.phase.part2_prep': 'Part 2 · Preparation',
  'interview.phase.part2_speaking': 'Part 2 · Long turn',
  'interview.phase.part2_followup': 'Part 2 · Follow-up',
  'interview.phase.part3': 'Part 3 · Discussion',
  'interview.phase.scoring': 'Finishing up',
  'interview.phase.complete': 'Complete',

  // Scores. The disclaimer is a string like any other so it can be reviewed
  // and translated, rather than living inside a component where nobody edits
  // it.
  'score.estimateFull':
    'This is an AI estimate to guide your practice, not an official IELTS ' +
    'score. Only a certified examiner can give you a real band.',
  'score.estimateShort': 'AI estimate — not an official IELTS score.',

  // Errors the learner can act on.
  'error.microphoneBlocked':
    'Microphone access is blocked. Enable it in Settings to record your answers.',
  'error.microphoneNeeded':
    'Microphone access is needed to record your answer.',
  'error.tooShort':
    'That was too short to send. Hold the button while you speak.',
  'error.generic': 'Something went wrong. Please try again.',
  'error.offline': 'You are offline. Your work is saved and will sync.',
} as const;
