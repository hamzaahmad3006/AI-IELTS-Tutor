/** Splash screen (UI only). Logic lives in useSplash. */

import React from 'react';
import { StatusBar, StyleSheet, View } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { AppText, Icon, Logo } from '../../components';
import { PALETTE, RADIUS, SPACING, LAYOUT } from '../../constants';
import { useSplash } from './useSplash';

export const Splash: React.FC = () => {
  const { brandMark, displayName, tagline, poweredBy } = useSplash();

  return (
    <LinearGradient
      colors={[PALETTE.indigoTint, PALETTE.indigo]}
      start={{ x: 0.2, y: 0 }}
      end={{ x: 0.8, y: 1 }}
      style={styles.fill}
    >
      <StatusBar barStyle="light-content" backgroundColor={PALETTE.indigo} />
      <View style={styles.center}>
        <View style={styles.logoTile}>
          <Logo size={LAYOUT.logoSizeSplash * 0.62} />
          <AppText variant="labelMd" color="textPrimary" style={styles.mark}>
            {brandMark}
          </AppText>
        </View>

        <AppText variant="headlineLg" color="textInverse" style={styles.title}>
          {displayName}
        </AppText>
        <AppText variant="bodyLg" color="textInverse" align="center" style={styles.tagline}>
          {tagline}
        </AppText>

        <View style={styles.poweredRow}>
          <Icon name="sparkle" size={16} color="accent" />
          <AppText variant="labelSm" color="textInverse" style={styles.powered}>
            {poweredBy}
          </AppText>
        </View>

        <View style={styles.track}>
          <View style={styles.trackFill} />
        </View>
      </View>
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  fill: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: SPACING.xl },
  logoTile: {
    width: LAYOUT.logoSizeSplash + 40,
    height: LAYOUT.logoSizeSplash + 40,
    backgroundColor: PALETTE.white,
    borderRadius: RADIUS.lg,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: SPACING.xxl,
  },
  mark: { marginTop: SPACING.xxs, letterSpacing: 1 },
  title: { marginBottom: SPACING.sm },
  tagline: { opacity: 0.85 },
  poweredRow: { flexDirection: 'row', alignItems: 'center', marginTop: SPACING.md },
  powered: { opacity: 0.75, marginLeft: SPACING.xs },
  track: {
    width: 220,
    height: 5,
    borderRadius: RADIUS.pill,
    backgroundColor: 'rgba(255,255,255,0.25)',
    marginTop: SPACING.xxl,
    overflow: 'hidden',
  },
  trackFill: {
    width: '55%',
    height: '100%',
    borderRadius: RADIUS.pill,
    backgroundColor: PALETTE.teal400,
  },
});
