/**
 * Typed mock fixtures mirroring the approved Stitch designs.
 * Used while `API_CONFIG.useMock` is true so the UI is fully demonstrable
 * before the backend exists.
 */

import type {
  AuthResponse,
  DashboardData,
  SpeakingSession,
  WritingFeedback,
} from '../../types';

export const MOCK_AUTH: AuthResponse = {
  user: {
    id: 'usr_mock_1',
    email: 'sarah@example.com',
    fullName: 'Sarah',
    role: 'learner',
  },
  tokens: {
    accessToken: 'mock.access.token',
    refreshToken: 'mock.refresh.token',
    tokenType: 'bearer',
    expiresIn: 900,
  },
};

export const MOCK_DASHBOARD: DashboardData = {
  greetingName: 'Sarah',
  streakDays: 5,
  prediction: {
    predictedBand: 7.0,
    confidence: 0.72,
    distanceToTarget: 0.5,
    basedOnSessions: 3,
    progressToTarget: 0.78,
  },
  coach: {
    id: 'coach_1',
    title: 'Daily Coach',
    message: "You're doing great in Lexical Resource!",
  },
  modules: [
    { module: 'speaking', currentLevel: 7.5, isActive: true },
    { module: 'writing', currentLevel: 6.5, isActive: false },
    { module: 'reading', currentLevel: 7.0, isActive: false },
    { module: 'listening', currentLevel: 7.5, isActive: false },
  ],
  checklist: [
    {
      id: 'task_1',
      title: 'Speaking Drill - Part 2 Topics',
      subtitle: 'Completed 10:30 AM',
      isCompleted: true,
      completedAt: '2026-07-22T10:30:00Z',
      priority: null,
    },
    {
      id: 'task_2',
      title: '1 Writing Task 1 Essay',
      subtitle: 'Priority: High',
      isCompleted: false,
      completedAt: null,
      priority: 'high',
    },
    {
      id: 'task_3',
      title: 'Vocabulary: Synonyms for "Important"',
      subtitle: '15 min session',
      isCompleted: false,
      completedAt: null,
      priority: null,
    },
  ],
  checklistCompletionPct: 50,
};

export const MOCK_SPEAKING_SESSION: SpeakingSession = {
  sessionId: 'spk_mock_1',
  examinerName: 'AI Examiner Dr. Aris',
  part: 1,
  status: 'active',
  currentPrompt:
    "I'm listening. Please describe a place you visited recently that made a lasting impression.",
  confidenceBoost: 88,
  elapsedSeconds: 704,
  isMuted: false,
  transcript: [
    {
      id: 't1',
      speaker: 'examiner',
      isFinal: true,
      tokens: [
        { text: 'AI: Could you tell me about a recent trip you took?', kind: 'normal' },
      ],
    },
    {
      id: 't2',
      speaker: 'learner',
      isFinal: true,
      tokens: [
        { text: 'Well, last month I travelled to the ', kind: 'normal' },
        { text: 'scenic', kind: 'strong' },
        { text: ' coastal town of Amalfi in Italy. It was an absolutely ', kind: 'normal' },
        { text: 'breathtaking', kind: 'suggestion' },
        { text: ' experience. The cliffs were so steep and the water was a deep, crystal-clear blue...', kind: 'normal' },
      ],
    },
    {
      id: 't3',
      speaker: 'learner',
      isFinal: false,
      tokens: [
        {
          text: 'I particularly enjoyed the local cuisine, especially the fresh seafood which was caught daily by the local fishermen. The atmosphere was incredibly vibrant yet peaceful...',
          kind: 'normal',
        },
      ],
    },
  ],
};

export const MOCK_WRITING_FEEDBACK: WritingFeedback = {
  attemptId: 'wr_mock_1',
  taskLabel: 'Writing Task 2',
  title: 'Detailed AI Feedback',
  analysisSummary:
    'Analysis of your essay on "The Impact of Global Warming on Coastal Cities." Focus on Lexical Resource and Grammar.',
  overallBand: 6.5,
  bandLabel: 'Competent User',
  criteria: {
    taskResponse: 7.0,
    coherenceCohesion: 6.5,
    lexicalResource: 6.0,
    grammaticalRange: 6.5,
  },
  masterTip:
    "Use cohesive devices like 'Furthermore' or 'Consequently' to improve your flow.",
  draftSegments: [
    { text: 'Nowadays, global warming is becoming a ', kind: 'normal' },
    { text: 'serios', kind: 'error' },
    { text: ' issue for everyone. Many coastal cities ', kind: 'normal' },
    { text: 'is', kind: 'error' },
    { text: ' facing great risks because of rising sea levels. Governments ', kind: 'normal' },
    { text: 'around the world', kind: 'suggestion' },
    { text: ' must take actions to protect their citizens.', kind: 'normal' },
  ],
  modelEssay:
    'Nowadays, global warming is becoming a serious issue for everyone. Many coastal cities are facing significant risks due to rising sea levels, and governments worldwide must take decisive action to protect their citizens.',
  wordCount: 184,
  improvements: [
    {
      id: 'imp_1',
      icon: 'edit',
      title: 'Spelling & Grammar',
      description:
        'You had 3 spelling errors and 2 subject-verb agreement issues. Consistent practice with "serios" vs "serious" is needed.',
    },
    {
      id: 'imp_2',
      icon: 'sparkle',
      title: 'Vocabulary Precision',
      description:
        'Replace generic words like "bad" and "problem" with topic-specific vocabulary like "detrimental" and "ecological crisis."',
    },
  ],
};
