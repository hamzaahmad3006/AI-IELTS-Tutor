/** Profile & settings screen (UI only). Logic in useProfile. */

import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import {
  AppText,
  BandSlider,
  Button,
  Card,
  ConsentSheet,
  DatePickerSheet,
  Icon,
  ScreenContainer,
  useTheme,
} from '../../../components';
import { getBandColor, RADIUS, SPACING } from '../../../constants';
import { useProfile } from './useProfile';

const STUDY_TIMES = [15, 30, 60, 90];

export const Profile: React.FC = () => {
  const theme = useTheme();
  const {
    user,
    profile,
    isLoading,
    isSaving,
    error,
    themeMode,
    onChangeTargetBand,
    onChangeDailyMinutes,
    onToggleTheme,
    onLogout,
    consentSheetOpen,
    openConsentSheet,
    closeConsentSheet,
    onSaveConsent,
    dateSheetOpen,
    openDateSheet,
    closeDateSheet,
    onChangeExamDate,
  } = useProfile();

  if (isLoading) {
    return (
      <ScreenContainer>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
        <ConsentSheet
        visible={consentSheetOpen}
        value={{
          consentAi: profile?.consentAi ?? false,
          consentVoice: profile?.consentVoice ?? false,
        }}
        onClose={closeConsentSheet}
        onSave={onSaveConsent}
        isSaving={isSaving}
      />

      <DatePickerSheet
        visible={dateSheetOpen}
        value={profile?.examDate ?? null}
        title="When is your exam?"
        onClose={closeDateSheet}
        onSelect={onChangeExamDate}
        onClear={() => onChangeExamDate(null)}
        isSaving={isSaving}
      />
    </ScreenContainer>
    );
  }

  return (
    <ScreenContainer scroll>
      <AppText variant="headlineMobile" style={styles.title}>
        Profile
      </AppText>

      {/* Identity */}
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

      {profile ? (
        <>
          {/* Goal */}
          <Card style={styles.card}>
            <View style={styles.rowBetween}>
              <AppText variant="titleLg">Target band</AppText>
              <AppText
                variant="headlineMd"
                style={{ color: getBandColor(profile.targetBand) }}
              >
                {profile.targetBand.toFixed(1)}
              </AppText>
            </View>
            <BandSlider value={profile.targetBand} onChange={onChangeTargetBand} />
            <AppText variant="labelSm" color="textMuted" style={styles.hint}>
              {profile.examType === 'academic' ? 'Academic' : 'General Training'}
              {profile.examDate ? ` · exam ${profile.examDate}` : ''}
              {profile.cefrLevel ? ` · ${profile.cefrLevel}` : ''}
            </AppText>
          </Card>

          {/* Study time */}
          <Card style={styles.card}>
            <AppText variant="titleLg" style={styles.cardTitle}>
              Daily study time
            </AppText>
            <View style={styles.chipRow}>
              {STUDY_TIMES.map((minutes) => {
                const selected = profile.dailyMinutes === minutes;
                return (
                  <Button
                    key={minutes}
                    title={`${minutes} min`}
                    variant={selected ? 'primary' : 'secondary'}
                    fullWidth={false}
                    onPress={() => onChangeDailyMinutes(minutes)}
                    style={styles.chip}
                  />
                );
              })}
            </View>
          </Card>

          {/* Baselines */}
          <Card style={styles.card}>
            <AppText variant="titleLg" style={styles.cardTitle}>
              Starting levels
            </AppText>
            {(['speaking', 'writing', 'reading', 'listening'] as const).map((module) => {
              const band = profile.baselines[module];
              return (
                <View key={module} style={styles.baselineRow}>
                  <AppText variant="bodyMd" style={styles.baselineLabel}>
                    {module.charAt(0).toUpperCase() + module.slice(1)}
                  </AppText>
                  <AppText variant="labelMd" color="textSecondary">
                    {band !== null ? band.toFixed(1) : 'Not set'}
                  </AppText>
                </View>
              );
            })}
          </Card>
        </>
      ) : (
        <Card style={styles.card} backgroundToken="cardAlt">
          <AppText variant="titleLg">No plan yet</AppText>
          <AppText variant="bodyMd" color="textSecondary" style={styles.hint}>
            Complete onboarding to set your target band and study schedule.
          </AppText>
        </Card>
      )}

      {isSaving ? (
        <AppText variant="labelSm" color="textMuted" style={styles.saving}>
          Saving…
        </AppText>
      ) : null}
      {error ? (
        <AppText variant="labelMd" color="error" style={styles.saving}>
          {error}
        </AppText>
      ) : null}

      {/* Exam date */}
      <Card style={styles.card}>
        <View style={styles.rowBetween}>
          <View>
            <AppText variant="bodyMd">Exam date</AppText>
            <AppText variant="labelSm" color="textSecondary">
              {profile?.examDate ?? 'Not set'}
            </AppText>
          </View>
          <Button
            title={profile?.examDate ? 'Change' : 'Set date'}
            variant="secondary"
            fullWidth={false}
            onPress={openDateSheet}
          />
        </View>
      </Card>

      {/* Privacy */}
      <Card style={styles.card}>
        <View style={styles.rowBetween}>
          <View style={styles.consentSummary}>
            <AppText variant="bodyMd">Privacy & consent</AppText>
            <AppText variant="labelSm" color="textSecondary">
              {`AI processing ${profile?.consentAi ? 'on' : 'off'} · Voice ${
                profile?.consentVoice ? 'on' : 'off'
              }`}
            </AppText>
          </View>
          <Button
            title="Manage"
            variant="secondary"
            fullWidth={false}
            onPress={openConsentSheet}
          />
        </View>
      </Card>

      {/* Appearance */}
      <Card style={styles.card}>
        <View style={styles.rowBetween}>
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
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { marginVertical: SPACING.md },
  card: { marginBottom: SPACING.md },
  cardTitle: { marginBottom: SPACING.sm },
  userRow: { flexDirection: 'row', alignItems: 'center' },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: 'center',
    justifyContent: 'center',
  },
  userText: { marginLeft: SPACING.md, flex: 1 },
  rowBetween: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: SPACING.sm,
  },
  hint: { marginTop: SPACING.sm },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap' },
  chip: {
    marginRight: SPACING.xs,
    marginBottom: SPACING.xs,
    paddingHorizontal: SPACING.md,
    borderRadius: RADIUS.pill,
  },
  baselineRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: SPACING.xs,
  },
  baselineLabel: { flex: 1 },
  saving: { marginBottom: SPACING.sm },
  consentSummary: { flex: 1, paddingRight: SPACING.sm },
  logout: { marginTop: SPACING.xs },
});
