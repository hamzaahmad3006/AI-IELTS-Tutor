/**
 * The one journey that has to work.
 *
 * Register, onboard, submit an essay, see a band. If that path is broken the
 * app has no purpose, and every other test passing is irrelevant.
 *
 * Deliberately one flow rather than a suite per screen. E2E tests are slow,
 * flaky and expensive to maintain, and a large suite of them decays into
 * something people skip. The unit and smoke suites already cover breadth;
 * this covers the thing that must never break.
 *
 * Requires a running backend the device can reach. See e2e/README.md.
 */

const { device, element, by, expect: detoxExpect } = require('detox');

const unique = () => `e2e-${Date.now()}@example.com`;

const ESSAY = (
  'Urbanisation has reshaped how populations live and work across the world. ' +
  'Cities concentrate labour and capital, which raises productivity and creates ' +
  'employment on a scale rural areas cannot match. However, growth has outpaced ' +
  'the provision of housing, water and transport in many places, and the cost ' +
  'falls hardest on the poorest residents. Governments that plan for migration ' +
  'before it arrives consistently achieve better outcomes than those that react ' +
  'to overcrowding after the fact.'
).repeat(2);

describe('Critical path', () => {
  beforeAll(async () => {
    await device.launchApp({
      newInstance: true,
      // Granted up front so the run never blocks on a system dialog that
      // Detox cannot dismiss on every Android version.
      permissions: { microphone: 'YES' },
    });
  });

  it('registers, onboards, and scores an essay', async () => {
    const email = unique();

    // --- Register ---
    await element(by.id('auth-go-to-register')).tap();
    await element(by.id('register-name')).typeText('E2E Learner');
    await element(by.id('register-email')).typeText(email);
    await element(by.id('register-password')).typeText('StrongPass123');
    await element(by.id('register-submit')).tap();

    // --- Onboard ---
    // Waited for rather than asserted immediately: registration hashes a
    // password with Argon2, which is deliberately slow.
    await waitFor(element(by.id('onboarding-exam-academic')))
      .toBeVisible()
      .withTimeout(20_000);
    await element(by.id('onboarding-exam-academic')).tap();
    await element(by.id('onboarding-continue')).tap();

    await waitFor(element(by.id('onboarding-consent-ai')))
      .toBeVisible()
      .withTimeout(10_000);
    await element(by.id('onboarding-consent-ai')).tap();
    await element(by.id('onboarding-finish')).tap();

    // --- Write and submit ---
    await waitFor(element(by.id('home-practice-writing')))
      .toBeVisible()
      .withTimeout(20_000);
    await element(by.id('home-practice-writing')).tap();

    await waitFor(element(by.id('writing-essay-input')))
      .toBeVisible()
      .withTimeout(10_000);
    await element(by.id('writing-essay-input')).typeText(ESSAY);
    await element(by.id('writing-submit')).tap();

    // --- Band ---
    // A generous timeout: this waits on a real model, and a flaky failure
    // here would train people to ignore the suite.
    await waitFor(element(by.id('writing-band')))
      .toBeVisible()
      .withTimeout(90_000);

    // The disclaimer travels with the band. A score shown without it is the
    // app implying an official result.
    await detoxExpect(element(by.id('estimate-note'))).toBeVisible();
  });

  it('keeps the session across a restart', async () => {
    // Tokens live in the Android Keystore. This is the assertion the unit
    // tests cannot make: whether the entry actually survives a cold start on
    // real hardware.
    await device.launchApp({ newInstance: false });
    await device.reloadReactNative();

    await waitFor(element(by.id('home-practice-writing')))
      .toBeVisible()
      .withTimeout(20_000);
  });
});
