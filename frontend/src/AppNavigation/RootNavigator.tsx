/** Root native-stack navigator wiring the whole app together. */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Splash } from '../screens/Splash/Splash';
import { Interview } from '../screens/Speaking/Interview/Interview';
import { Feedback } from '../screens/Writing/Feedback/Feedback';
import { Practice as ReadingPractice } from '../screens/Reading/Practice/Practice';
import { Practice as WritingPractice } from '../screens/Writing/Practice/Practice';
import { Practice as ListeningPractice } from '../screens/Listening/Practice/Practice';
import { AuthNavigator } from './AuthNavigator';
import { OnboardingNavigator } from './OnboardingNavigator';
import { MainTabNavigator } from './MainTabNavigator';
import type { RootStackParamList } from '../types';

const Stack = createNativeStackNavigator<RootStackParamList>();

export const RootNavigator: React.FC = () => (
  <Stack.Navigator
    initialRouteName="Splash"
    screenOptions={{ headerShown: false }}
  >
    <Stack.Screen name="Splash" component={Splash} />
    <Stack.Screen name="Auth" component={AuthNavigator} />
    <Stack.Screen name="Onboarding" component={OnboardingNavigator} />
    <Stack.Screen name="Main" component={MainTabNavigator} />
    <Stack.Screen
      name="SpeakingInterview"
      component={Interview}
      options={{ presentation: 'fullScreenModal' }}
    />
    <Stack.Screen name="WritingFeedback" component={Feedback} />
    <Stack.Screen name="WritingPractice" component={WritingPractice} />
    <Stack.Screen name="ReadingPractice" component={ReadingPractice} />
    <Stack.Screen name="ListeningPractice" component={ListeningPractice} />
  </Stack.Navigator>
);
