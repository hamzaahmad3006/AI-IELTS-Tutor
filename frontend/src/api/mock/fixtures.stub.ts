/**
 * Release stand-in for the fixtures module.
 *
 * The fixtures are only reachable behind `__DEV__`, so they can never be shown
 * to a user -- but a static import puts them in the bundle regardless of
 * reachability, because Metro builds its dependency graph from the import
 * graph and not from what actually runs. Roughly 22 KB of invented essays,
 * bands and feedback was therefore shipping to every device.
 *
 * In production builds `@fixtures` resolves here instead (see babel.config.js).
 * Every export keeps its real type via `typeof import`, so the type checker
 * still validates the call sites it guards; at runtime each one is undefined,
 * which is safe precisely because nothing in a release build reads them.
 *
 * A test asserts the release bundle contains no fixture text, so this cannot
 * silently stop working.
 */

const stub = {} as typeof import('./fixtures');

export const {
  MOCK_AUTH,
  MOCK_DASHBOARD,
  MOCK_PROGRESS,
  MOCK_TREND,
  MOCK_PREDICTION,
  MOCK_PROFILE,
  MOCK_WEAKNESSES,
  MOCK_ADAPTIVE_DIFFICULTY,
  MOCK_RECOMMENDATIONS,
  MOCK_READING_PASSAGE,
  MOCK_READING_RESULT,
  MOCK_LISTENING_CLIP,
  MOCK_LISTENING_RESULT,
  MOCK_WRITING_RESULT,
  MOCK_SPEAKING_RESULT,
  MOCK_SPEAKING_SESSION,
  MOCK_WRITING_FEEDBACK,
  MOCK_DATA_EXPORT,
  MOCK_INSIGHTS,
  MOCK_SPEAKING_QUESTIONS,
  MOCK_DIAGNOSTIC_SET,
  MOCK_DIAGNOSTIC_RESULT,
  MOCK_STUDY_PLAN,
  MOCK_MOCK_TEST,
  MOCK_MOCK_RESULT,
} = stub;
