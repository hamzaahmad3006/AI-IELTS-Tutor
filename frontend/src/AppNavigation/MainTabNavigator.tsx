/** Bottom tab navigator: Home, Practice, Progress, Coach, Profile. */

import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Home } from '../screens/Dashboard/Home/Home';
import { Practice } from '../screens/Dashboard/Practice/Practice';
import { Progress } from '../screens/Dashboard/Progress/Progress';
import { Coach } from '../screens/Dashboard/Coach/Coach';
import { Profile } from '../screens/Dashboard/Profile/Profile';
import { Icon, useTheme } from '../components';
import { LAYOUT, ICONS, type IconName } from '../constants';
import type { MainTabParamList } from '../types';

const Tab = createBottomTabNavigator<MainTabParamList>();

const TAB_ICON: Record<keyof MainTabParamList, IconName> = {
  Home: ICONS.home,
  Practice: ICONS.practice,
  Progress: ICONS.progress,
  Coach: ICONS.coach,
  Profile: ICONS.profile,
};

export const MainTabNavigator: React.FC = () => {
  const theme = useTheme();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: theme.colors.accent,
        tabBarInactiveTintColor: theme.colors.textMuted,
        tabBarStyle: {
          height: LAYOUT.tabBarHeight,
          paddingBottom: 8,
          paddingTop: 8,
          backgroundColor: theme.colors.card,
          borderTopColor: theme.colors.border,
        },
        tabBarIcon: ({ color }) => (
          <TabIcon name={TAB_ICON[route.name]} color={color} />
        ),
      })}
    >
      <Tab.Screen name="Home" component={Home} />
      <Tab.Screen name="Practice" component={Practice} />
      <Tab.Screen name="Progress" component={Progress} />
      <Tab.Screen name="Coach" component={Coach} />
      <Tab.Screen name="Profile" component={Profile} />
    </Tab.Navigator>
  );
};

/** Small wrapper so the tab color (a raw string) drives our SVG Icon. */
const TabIcon: React.FC<{ name: IconName; color: string }> = ({
  name,
  color,
}) => <Icon name={name} size={24} overrideColor={color} />;
