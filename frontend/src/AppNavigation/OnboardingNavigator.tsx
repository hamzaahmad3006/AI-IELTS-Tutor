/** Onboarding stack. Only TargetBand is implemented in this milestone. */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { TargetBand } from '../screens/Onboarding/TargetBand/TargetBand';
import { ExamSetup } from '../screens/Onboarding/ExamSetup/ExamSetup';
import type { OnboardingStackParamList } from '../types';

const Stack = createNativeStackNavigator<OnboardingStackParamList>();

export const OnboardingNavigator: React.FC = () => (
  <Stack.Navigator
    initialRouteName="TargetBand"
    screenOptions={{ headerShown: false }}
  >
    <Stack.Screen name="TargetBand" component={TargetBand} />
    <Stack.Screen name="ExamSetup" component={ExamSetup} />
  </Stack.Navigator>
);
