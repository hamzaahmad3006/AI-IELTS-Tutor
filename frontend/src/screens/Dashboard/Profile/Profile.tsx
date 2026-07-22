/** Profile & settings (UI only). */

import React from 'react';
import { StyleSheet, View } from 'react-native';
import {
  AppText,
  Button,
  Card,
  Icon,
  ScreenContainer,
  useTheme,
} from '../../../components';
import { SPACING } from '../../../constants';
import { useProfile } from './useProfile';

export const Profile: React.FC = () => {
  const theme = useTheme();
  const { user, themeMode, onToggleTheme, onLogout } = useProfile();

  return (
    <ScreenContainer scroll>
      <AppText variant="headlineMobile" style={styles.title}>
        Profile
      </AppText>

      <Card style={styles.card}>
        <View style={styles.userRow}>
          <View style={[styles.avatar, { backgroundColor: theme.colors.primaryContainer }]}>
            <Icon name="profile" size={26} color="primary" />
          </View>
          <View style={styles.userText}>
            <AppText variant="titleLg">{user?.fullName ?? 'Guest Learner'}</AppText>
            <AppText variant="bodySm" color="textSecondary">
              {user?.email ?? 'Not signed in'}
            </AppText>
          </View>
        </View>
      </Card>

      <Card style={styles.card}>
        <View style={styles.settingRow}>
          <AppText variant="bodyMd">Appearance</AppText>
          <Button
            title={themeMode === 'light' ? 'Switch to Dark' : 'Switch to Light'}
            variant="secondary"
            fullWidth={false}
            onPress={onToggleTheme}
          />
        </View>
      </Card>

      <Button
        title="Log Out"
        variant="secondary"
        onPress={onLogout}
        style={styles.logout}
      />
    </ScreenContainer>
  );
};

const styles = StyleSheet.create({
  title: { marginVertical: SPACING.md },
  card: { marginBottom: SPACING.md },
  userRow: { flexDirection: 'row', alignItems: 'center' },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: 'center',
    justifyContent: 'center',
  },
  userText: { marginLeft: SPACING.md },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  logout: { marginTop: SPACING.md },
});
