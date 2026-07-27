import {
  nextStep,
  onboardingReducer,
  prevStep,
  resetOnboarding,
  setStep,
  setTargetBand,
  updateDraft,
} from '../slices/onboardingSlice';

const init = () => onboardingReducer(undefined, { type: '@@init' });

describe('onboardingSlice', () => {
  it('starts on step 1 with sensible defaults', () => {
    const state = init();
    expect(state.step).toBe(1);
    expect(state.draft.examType).toBe('academic');
    expect(state.draft.consentAi).toBe(false);
  });

  it('advances and rewinds within bounds', () => {
    let state = init();
    state = onboardingReducer(state, nextStep());
    expect(state.step).toBe(2);
    state = onboardingReducer(state, prevStep());
    expect(state.step).toBe(1);
    // Cannot go below the first step.
    state = onboardingReducer(state, prevStep());
    expect(state.step).toBe(1);
  });

  it('never advances past the last step', () => {
    let state = onboardingReducer(init(), setStep(4));
    state = onboardingReducer(state, nextStep());
    expect(state.step).toBe(4);
  });

  it('sets the target band', () => {
    const state = onboardingReducer(init(), setTargetBand(8));
    expect(state.draft.targetBand).toBe(8);
  });

  it('merges partial draft updates without dropping other fields', () => {
    let state = onboardingReducer(init(), updateDraft({ examType: 'general' }));
    state = onboardingReducer(state, updateDraft({ dailyMinutes: 90 }));
    expect(state.draft.examType).toBe('general');
    expect(state.draft.dailyMinutes).toBe(90);
    // Untouched fields keep their defaults.
    expect(state.draft.selfLevel).toBe('intermediate');
  });

  it('resets back to the initial wizard state', () => {
    let state = onboardingReducer(init(), updateDraft({ examType: 'general' }));
    state = onboardingReducer(state, setStep(3));
    expect(onboardingReducer(state, resetOnboarding())).toEqual(init());
  });
});
