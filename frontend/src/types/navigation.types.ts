/** Strongly-typed navigation param lists. */

import type { NavigatorScreenParams } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import type { IeltsModule } from './common.types';
import type { SpeakingPart } from './speaking.types';

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
};

export type OnboardingStackParamList = {
  Welcome: undefined;
  TargetBand: undefined;
  ExamSetup: undefined;
  Diagnostic: undefined;
};

export type MainTabParamList = {
  Home: undefined;
  Practice: undefined;
  Progress: undefined;
  Coach: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  Splash: undefined;
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Onboarding: NavigatorScreenParams<OnboardingStackParamList>;
  Main: NavigatorScreenParams<MainTabParamList>;
  SpeakingInterview: { module?: IeltsModule } | undefined;
  WritingFeedback: { attemptId: string };
  WritingPractice: undefined;
  ReadingPractice: undefined;
  ListeningPractice: undefined;
  SpeakingPractice: undefined;
  SpeakingSession: undefined;
  SpeakingParts: { part: SpeakingPart; full?: boolean };
  History: undefined;
  Plan: undefined;
  VocabularyReview: undefined;
  GrammarLessons: undefined;
};

// Convenience screen-props helpers
export type RootScreenProps<T extends keyof RootStackParamList> =
  NativeStackScreenProps<RootStackParamList, T>;

export type AuthScreenProps<T extends keyof AuthStackParamList> =
  NativeStackScreenProps<AuthStackParamList, T>;

export type OnboardingScreenProps<T extends keyof OnboardingStackParamList> =
  NativeStackScreenProps<OnboardingStackParamList, T>;

export type MainTabScreenProps<T extends keyof MainTabParamList> =
  BottomTabScreenProps<MainTabParamList, T>;

// Global type augmentation so useNavigation() is typed everywhere.
declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
