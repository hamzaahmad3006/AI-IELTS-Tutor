/** Placeholder body for screens not yet implemented in this milestone. */

import React from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText } from '../AppText/AppText';
import { Icon } from '../Icon/Icon';
import { ScreenContainer } from '../ScreenContainer/ScreenContainer';
import { SPACING, type IconName } from '../../constants';

interface ComingSoonProps {
  title: string;
  subtitle: string;
  icon: IconName;
}

export const ComingSoon: React.FC<ComingSoonProps> = ({
  title,
  subtitle,
  icon,
}) => (
  <ScreenContainer>
    <View style={styles.center}>
      <Icon name={icon} size={48} color="primary" />
      <AppText variant="headlineMd" align="center" style={styles.title}>
        {title}
      </AppText>
      <AppText variant="bodyMd" color="textSecondary" align="center">
        {subtitle}
      </AppText>
    </View>
  </ScreenContainer>
);

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { marginTop: SPACING.md, marginBottom: SPACING.xs },
});
