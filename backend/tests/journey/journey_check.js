/**
 * End-to-end user-journey check.
 *
 * Drives the live API in the exact order the mobile app's screens do:
 *   register -> onboarding -> home -> practice hub -> reading / listening /
 *   writing / speaking -> progress -> coach -> profile edit -> history -> logout
 *
 * Uses Node's built-in fetch (Node 18+), so it has no dependencies.
 *
 * Usage:  node tests/journey/journey_check.js [baseUrl]
 *         BASE_URL=http://localhost:8000/v1 node tests/journey/journey_check.js
 */

const BASE =
  process.argv[2] || process.env.BASE_URL || 'http://localhost:8000/v1';

function assert(condition, message) {
  if (!condition) {
    throw new Error('FAILED: ' + message);
  }
}

const step = (n, message) => console.log(`  ${n}. ${message}`);

async function call(method, path, { token, body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(BASE + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(
      `${method} ${path} -> ${response.status} ${text.slice(0, 300)}`,
    );
  }
  return { status: response.status, data };
}

const ESSAY =
  'Technology has transformed modern society in profound ways. Some argue it ' +
  'complicates life while others believe it simplifies it. In my opinion the ' +
  'benefits clearly outweigh the drawbacks, since communication is instant and ' +
  'knowledge is freely available. Furthermore, automation frees people to focus ' +
  'on creative and meaningful work.';

const TRANSCRIPT =
  'Well, the place I would like to describe is a small coastal town I visited ' +
  'last summer. It was genuinely breathtaking, with steep cliffs and crystal ' +
  'clear water, and I especially enjoyed the local seafood and the vibrant yet ' +
  'peaceful atmosphere there.';

async function main() {
  const email = `journey_${Date.now()}@example.com`;
  const password = 'StrongPass123';
  console.log(`USER JOURNEY against ${BASE}`);

  // 1. Splash -> Auth -> Register
  let res = await call('POST', '/auth/register', {
    body: { fullName: 'Journey User', email, password },
  });
  assert(res.status === 201, 'register returns 201');
  const token = res.data.tokens.accessToken;
  const refreshToken = res.data.tokens.refreshToken;
  step(1, 'Register -> tokens received');

  // 2. Onboarding (TargetBand -> ExamSetup submit)
  res = await call('POST', '/onboarding', {
    token,
    body: {
      examType: 'academic',
      selfLevel: 'intermediate',
      targetBand: 7.5,
      examDate: '2026-12-01',
      dailyMinutes: 60,
      consentVoice: true,
      consentAi: true,
    },
  });
  assert(res.data.targetBand === 7.5, 'onboarding stores target band');
  step(2, 'Onboarding submitted -> profile created');

  // 3. Home dashboard
  res = await call('GET', '/analytics/overview', { token });
  assert(res.data.modules.length === 4, 'dashboard returns 4 modules');
  step(3, `Home loaded (greeting "${res.data.greetingName}")`);

  // 4. Practice hub -> adaptive levels
  res = await call('GET', '/me/adaptive-difficulty', { token });
  assert(res.data.modules.length === 4, 'adaptive levels for 4 modules');
  step(4, 'Practice hub -> adaptive levels');

  // 5. Reading practice
  const passage = (await call('GET', '/reading/passages', { token })).data;
  const rIds = passage.questions.map((q) => q.id);
  res = await call('POST', '/reading/attempts', {
    token,
    body: {
      passageId: passage.id,
      answers: { [rIds[0]]: 'China', [rIds[1]]: 'true', [rIds[2]]: 'black' },
    },
  });
  assert(res.data.band > 0, 'reading graded');
  step(5, `Reading: ${res.data.rawScore}/${res.data.totalQuestions} -> band ${res.data.band}`);

  // 6. Listening practice
  const clip = (await call('GET', '/listening/clips', { token })).data;
  const lIds = clip.questions.map((q) => q.id);
  res = await call('POST', '/listening/attempts', {
    token,
    body: {
      audioId: clip.id,
      answers: {
        [lIds[0]]: 'student card',
        [lIds[1]]: clip.questions[1].options[1],
        [lIds[2]]: 'ten',
      },
    },
  });
  assert(res.data.band > 0, 'listening graded');
  step(6, `Listening: ${res.data.rawScore}/${res.data.totalQuestions} -> band ${res.data.band}`);

  // 7. Writing practice (AI scored)
  res = await call('POST', '/writing/attempts', {
    token,
    body: { essayText: ESSAY, taskType: 2 },
  });
  assert(res.data.status === 'scored' && res.data.criteria, 'writing scored');
  step(7, `Writing: band ${res.data.overallBand} (4 criteria)`);

  // 8. Speaking practice (AI scored)
  res = await call('POST', '/speaking/attempts', {
    token,
    body: { transcript: TRANSCRIPT, part: 2, durationSec: 95 },
  });
  assert(res.data.status === 'scored' && res.data.criteria, 'speaking scored');
  step(8, `Speaking: band ${res.data.overallBand} (4 criteria)`);

  // 9. Progress screen
  const progress = (await call('GET', '/analytics/progress', { token })).data;
  const prediction = (await call('GET', '/analytics/prediction', { token })).data;
  assert(progress.totalAttempts === 4, 'progress counts all 4 attempts');
  step(9, `Progress: ${progress.totalAttempts} attempts, overall ${progress.overallBand}, predicted ${prediction.predictedOverall}`);

  // 10. Coach screen
  const recs = (await call('GET', '/me/recommendations', { token })).data;
  step(10, `Coach: ${recs.items.length} recommendation(s)`);

  // 11. Profile edit
  res = await call('PATCH', '/profile', { token, body: { targetBand: 8.0 } });
  assert(res.data.targetBand === 8.0, 'profile patch applied');
  step(11, 'Profile: target band updated 7.5 -> 8.0');

  // 12. History
  const history = (await call('GET', '/writing/history', { token })).data;
  assert(history.items.length >= 1, 'writing history populated');
  step(12, `History: ${history.items.length} writing attempt(s)`);

  // 13. Logout
  res = await call('POST', '/auth/logout', { token, body: { refreshToken } });
  assert(res.status === 204, 'logout returns 204');
  step(13, 'Logout -> refresh token revoked');

  console.log('\nFULL USER JOURNEY PASSED');
}

main().catch((error) => {
  console.error('JOURNEY FAIL:', error.message);
  process.exit(1);
});
