/** Onboarding wizard slice (multi-step draft state). */

import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { Band, OnboardingDraft, OnboardingState } from '@models';

const initialState: OnboardingState = {
  step: 1,
  totalSteps: 4,
  draft: {
    examType: 'academic',
    selfLevel: 'intermediate',
    targetBand: 7.0,
    examDate: null,
    dailyMinutes: 30,
    consentVoice: false,
    consentAi: false,
  },
};

const onboardingSlice = createSlice({
  name: 'onboarding',
  initialState,
  reducers: {
    setStep(state, action: PayloadAction<number>): void {
      state.step = action.payload;
    },
    nextStep(state): void {
      if (state.step < state.totalSteps) {
        state.step += 1;
      }
    },
    prevStep(state): void {
      if (state.step > 1) {
        state.step -= 1;
      }
    },
    setTargetBand(state, action: PayloadAction<Band>): void {
      state.draft.targetBand = action.payload;
    },
    updateDraft(state, action: PayloadAction<Partial<OnboardingDraft>>): void {
      state.draft = { ...state.draft, ...action.payload };
    },
    resetOnboarding(): OnboardingState {
      return initialState;
    },
  },
});

export const {
  setStep,
  nextStep,
  prevStep,
  setTargetBand,
  updateDraft,
  resetOnboarding,
} = onboardingSlice.actions;
export const onboardingReducer = onboardingSlice.reducer;
