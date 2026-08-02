/** Onboarding stack: welcome carousel, then the numbered setup steps. */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Welcome } from '../screens/Onboarding/Welcome/Welcome';
import { TargetBand } from '../screens/Onboarding/TargetBand/TargetBand';
import { ExamSetup } from '../screens/Onboarding/ExamSetup/ExamSetup';
import type { OnboardingStackParamList } from '../types';

const Stack = createNativeStackNavigator<OnboardingStackParamList>();

export const OnboardingNavigator: React.FC = () => (
  <Stack.Navigator
    initialRouteName="Welcome"
    screenOptions={{ headerShown: false }}
  >
    <Stack.Screen name="Welcome" component={Welcome} />
    <Stack.Screen name="TargetBand" component={TargetBand} />
    <Stack.Screen name="ExamSetup" component={ExamSetup} />
  </Stack.Navigator>
);
