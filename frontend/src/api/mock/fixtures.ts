/**
 * Typed mock fixtures mirroring the approved Stitch designs.
 * Used while `API_CONFIG.useMock` is true so the UI is fully demonstrable
 * before the backend exists.
 */

import type {
  AdaptiveDifficultyResponse,
  AuthResponse,
  DashboardData,
  ListeningClip,
  ListeningResult,
  PredictionResponse,
  ProfileResponse,
  ProgressResponse,
  ReadingPassage,
  ReadingResult,
  RecommendationsResponse,
  DataExport,
  InsightsResponse,
  SpeakingResult,
  SpeakingSession,
  TrendPoint,
  TrendResponse,
  WeaknessList,
  WritingFeedback,
  WritingResult,
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

export const MOCK_PROGRESS: ProgressResponse = {
  modules: [
    { module: 'speaking', attempts: 4, currentBand: 7.5, averageBand: 7.0 },
    { module: 'writing', attempts: 3, currentBand: 6.5, averageBand: 6.0 },
    { module: 'reading', attempts: 5, currentBand: 7.0, averageBand: 6.5 },
    { module: 'listening', attempts: 2, currentBand: 7.5, averageBand: 7.0 },
  ],
  overallBand: 7.0,
  totalAttempts: 14,
};

/** Deliberately non-monotonic, so the charts are exercised on a dip too. */
const trendPoints = (bands: number[], startDay: number): TrendPoint[] =>
  bands.map((band, i) => ({
    at: new Date(Date.UTC(2026, 5, startDay + i * 3)).toISOString(),
    band,
  }));

export const MOCK_TREND: TrendResponse = {
  modules: [
    { module: 'speaking', points: trendPoints([6.0, 6.5, 7.0, 7.5], 1) },
    { module: 'writing', points: trendPoints([5.5, 6.0, 6.5], 2) },
    { module: 'reading', points: trendPoints([6.0, 6.5, 6.0, 6.5, 7.0], 1) },
    { module: 'listening', points: trendPoints([7.0, 7.5], 4) },
  ],
  overall: trendPoints([6.0, 6.0, 6.5, 6.5, 6.5, 7.0, 7.0], 1),
};

export const MOCK_PREDICTION: PredictionResponse = {
  predictedOverall: 7.0,
  confidence: 0.72,
  horizonDate: '2026-10-15',
  modules: { speaking: 7.5, writing: 6.5, reading: 7.0, listening: 7.5 },
  velocityPerWeek: { speaking: 0.12, writing: 0.15, reading: 0.05, listening: 0.1 },
  note: 'Estimate based on your recent trajectory; not an official IELTS result.',
};

export const MOCK_PROFILE: ProfileResponse = {
  userId: 'usr_mock_1',
  examType: 'academic',
  selfLevel: 'intermediate',
  cefrLevel: 'B2',
  targetBand: 7.5,
  examDate: '2026-10-15',
  dailyMinutes: 60,
  baselines: { speaking: 6.5, writing: 6.0, reading: 6.5, listening: 7.0 },
  consentVoice: true,
  consentAi: true,
};

export const MOCK_WEAKNESSES: WeaknessList = {
  items: [
    { module: 'writing', tag: 'grammatical_range', severity: 0.44, occurrences: 3, lastSeenAt: '2026-07-24T09:00:00Z', resolved: false, priority: 0.42 },
    { module: 'reading', tag: 'true_false_notgiven', severity: 0.25, occurrences: 1, lastSeenAt: '2026-07-23T09:00:00Z', resolved: false, priority: 0.2 },
  ],
};

export const MOCK_ADAPTIVE_DIFFICULTY: AdaptiveDifficultyResponse = {
  modules: [
    { module: 'speaking', difficulty: 'medium', recentBand: 6.5, rationale: 'Recent average band 6.5 maps to medium.' },
    { module: 'writing', difficulty: 'medium', recentBand: 6.0, rationale: 'Recent average band 6.0 maps to medium.' },
    { module: 'reading', difficulty: 'hard', recentBand: 7.0, rationale: 'Recent average band 7.0 maps to hard.' },
    { module: 'listening', difficulty: 'medium', recentBand: null, rationale: 'No history yet; starting at medium.' },
  ],
};

export const MOCK_RECOMMENDATIONS: RecommendationsResponse = {
  items: [
    { module: 'writing', tag: 'grammatical_range', title: 'Grammatical Range & Accuracy', action: 'Practice complex sentence structures and review common grammar errors.', severity: 0.44, difficulty: 'medium' },
    { module: 'reading', tag: 'true_false_notgiven', title: 'True/False/Not Given', action: 'Practice distinguishing contradicted vs. absent information.', severity: 0.25, difficulty: 'hard' },
  ],
  message: 'Focus on these areas to move toward your target band.',
};

export const MOCK_READING_PASSAGE: ReadingPassage = {
  id: 'pa_mock_1',
  title: 'The History of Tea',
  body:
    'Tea is one of the most widely consumed beverages in the world. According to ' +
    'historical records, tea originated in China, where it was first used as a ' +
    'medicinal drink. The processing of the leaves determines the type of tea: ' +
    'green tea is barely oxidized, whereas black tea is produced by allowing the ' +
    'leaves to oxidize fully.',
  examType: 'academic',
  difficulty: 'medium',
  topic: 'history',
  wordCount: 62,
  questions: [
    { id: 'q1', type: 'mcq', prompt: 'Where did tea originate?', options: ['India', 'China', 'Japan', 'England'] },
    { id: 'q2', type: 'true_false_notgiven', prompt: 'Tea was first used as a medicinal drink.', options: ['true', 'false', 'not_given'] },
    { id: 'q3', type: 'short_answer', prompt: 'Which tea is produced by full oxidation?', options: null },
  ],
};

export const MOCK_READING_RESULT: ReadingResult = {
  attemptId: 'ra_mock_1',
  passageId: 'pa_mock_1',
  rawScore: 2,
  totalQuestions: 3,
  band: 6.0,
  perQuestion: [
    { questionId: 'q1', type: 'mcq', correct: true, submitted: 'China', correctAnswer: 'China', explanation: 'The passage states tea originated in China.' },
    { questionId: 'q2', type: 'true_false_notgiven', correct: true, submitted: 'true', correctAnswer: 'true', explanation: 'It was first used medicinally.' },
    { questionId: 'q3', type: 'short_answer', correct: false, submitted: 'green', correctAnswer: 'black', explanation: 'Black tea is fully oxidized.' },
  ],
};

export const MOCK_LISTENING_CLIP: ListeningClip = {
  id: 'au_mock_1',
  title: 'University Orientation',
  audioUrl: '/media/seed/audio/orientation.mp3',
  durationSec: 45,
  examType: 'academic',
  difficulty: 'medium',
  accent: 'British',
  questions: [
    { id: 'lq1', type: 'short_answer', prompt: 'What do you need to borrow books?', options: null },
    { id: 'lq2', type: 'mcq', prompt: 'Where is the main computer lab?', options: ['Library', 'Science building 2nd floor', 'Arts building', 'Science building 3rd floor'] },
    { id: 'lq3', type: 'form_completion', prompt: 'The library closes at ____ on weekdays.', options: null },
  ],
};

export const MOCK_LISTENING_RESULT: ListeningResult = {
  attemptId: 'la_mock_1',
  audioId: 'au_mock_1',
  rawScore: 3,
  totalQuestions: 3,
  band: 7.5,
  perQuestion: [
    { questionId: 'lq1', type: 'short_answer', correct: true, submitted: 'student card', correctAnswer: 'student card', explanation: 'You need your student card.', answerTimestamp: '00:12-00:16' },
    { questionId: 'lq2', type: 'mcq', correct: true, submitted: 'Science building 2nd floor', correctAnswer: 'Science building 2nd floor', explanation: 'Second floor of the science building.', answerTimestamp: '00:20-00:26' },
    { questionId: 'lq3', type: 'form_completion', correct: true, submitted: 'ten', correctAnswer: 'ten', explanation: 'Open until ten at night.', answerTimestamp: '00:06-00:10' },
  ],
};

export const MOCK_WRITING_RESULT: WritingResult = {
  attemptId: 'wr_mock_1',
  status: 'scored',
  taskType: 2,
  wordCount: 184,
  overallBand: 6.5,
  criteria: {
    taskResponse: 7.0,
    coherenceCohesion: 6.5,
    lexicalResource: 6.0,
    grammaticalRange: 6.5,
  },
  feedbackSummary:
    'Clear position and relevant ideas; widen your range of complex structures and precise vocabulary to lift your band.',
  improvedEssay:
    'Nowadays, technology has become increasingly important in our lives...',
};

export const MOCK_SPEAKING_RESULT: SpeakingResult = {
  attemptId: 'sp_mock_1',
  status: 'scored',
  part: 2,
  overallBand: 6.5,
  criteria: {
    fluencyCoherence: 6.5,
    lexicalResource: 6.0,
    grammaticalRange: 6.5,
    pronunciation: 7.0,
  },
  feedbackSummary:
    'Good pronunciation and fluency; reduce fillers and use a wider range of connectives.',
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

export const MOCK_DATA_EXPORT: DataExport = {
  exportedAt: '2026-06-01T10:00:00Z',
  account: {
    id: 'usr_mock_1',
    email: 'sarah@example.com',
    fullName: 'Sarah Ahmed',
    role: 'learner',
    emailVerified: true,
    createdAt: '2026-05-01T09:00:00Z',
  },
  profile: { target_band: 7.5, exam_type: 'academic' },
  writingAttempts: [{ overall_band: 6.5 }],
  speakingAttempts: [{ overall_band: 7.0 }],
  readingAttempts: [{ band: 7.0 }],
  listeningAttempts: [{ band: 7.5 }],
  weaknesses: [{ tag: 'article_use', severity: 0.4 }],
  vocabReviews: [],
};

export const MOCK_INSIGHTS: InsightsResponse = {
  strengths: [
    { module: 'listening', label: 'Listening', band: 7.5, detail: '+0.5 above your overall band' },
    { module: 'speaking', label: 'Speaking', band: 7.5, detail: '+0.5 above your overall band' },
  ],
  weaknesses: [
    { module: 'writing', label: 'Writing', tag: 'grammatical_range', tagLabel: 'Grammatical Range', severity: 0.44, occurrences: 3, detail: 'Seen 3 times in Writing' },
    { module: 'reading', label: 'Reading', tag: 'true_false_notgiven', tagLabel: 'True False Notgiven', severity: 0.25, occurrences: 1, detail: 'Seen 1 time in Reading' },
  ],
  consistency: {
    currentStreak: 5,
    longestStreak: 12,
    activeDaysLast30: 18,
    totalAttempts: 14,
    weeks: [
      { weekStart: '2026-04-13', attempts: 1, activeDays: 1 },
      { weekStart: '2026-04-20', attempts: 3, activeDays: 3 },
      { weekStart: '2026-04-27', attempts: 0, activeDays: 0 },
      { weekStart: '2026-05-04', attempts: 2, activeDays: 2 },
      { weekStart: '2026-05-11', attempts: 4, activeDays: 4 },
      { weekStart: '2026-05-18', attempts: 5, activeDays: 5 },
      { weekStart: '2026-05-25', attempts: 3, activeDays: 3 },
      { weekStart: '2026-06-01', attempts: 5, activeDays: 5 },
    ],
    measuredSpeakingMinutes: 42,
    timeNote: 'Only spoken responses are timed, so this covers Speaking only.',
  },
  summary: 'Listening is carrying you at band 7.5. Your biggest drag is grammatical range in writing.',
};
