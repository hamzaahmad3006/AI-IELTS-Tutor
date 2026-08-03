/** Primary / secondary / text button with the Teal CTA gradient. */

import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  View,
  type ViewStyle,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { AppText } from '../AppText/AppText';
import { Icon } from '../Icon/Icon';
import { useTheme } from '../theme/useTheme';
import { LAYOUT, RADIUS, SPACING, type IconName } from '@constants';

type ButtonVariant = 'primary' | 'secondary' | 'text';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
  loading?: boolean;
  disabled?: boolean;
  icon?: IconName;
  fullWidth?: boolean;
  style?: ViewStyle;
  testID?: string;
}

export const Button: React.FC<ButtonProps> = ({
  title,
  onPress,
  testID,
  variant = 'primary',
  loading = false,
  disabled = false,
  icon,
  fullWidth = true,
  style,
}) => {
  const theme = useTheme();
  const isDisabled = disabled || loading;

  const base: ViewStyle = {
    height: LAYOUT.buttonHeight,
    borderRadius: RADIUS.button,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    paddingHorizontal: SPACING.lg,
    opacity: isDisabled ? 0.6 : 1,
    ...(fullWidth ? { alignSelf: 'stretch' } : null),
  };

  const content = (
    <View style={styles.row}>
      {loading ? (
        <ActivityIndicator
          color={
            variant === 'primary' ? theme.colors.onAccent : theme.colors.primary
          }
        />
      ) : (
        <>
          <AppText
            variant="button"
            color={variant === 'primary' ? 'onAccent' : 'primary'}
          >
            {title}
          </AppText>
          {icon ? (
            <View style={styles.icon}>
              <Icon
                name={icon}
                size={20}
                color={variant === 'primary' ? 'onAccent' : 'primary'}
              />
            </View>
          ) : null}
        </>
      )}
    </View>
  );

  if (variant === 'primary') {
    return (
      <Pressable
        onPress={onPress}
        disabled={isDisabled}
        style={style}
        testID={testID}
      >
        <LinearGradient
          colors={[
            theme.colors.accentGradientStart,
            theme.colors.accentGradientEnd,
          ]}
          start={{ x: 0, y: 0 }}
          end={{ x: 0, y: 1 }}
          style={[base, theme.shadows.button]}
        >
          {content}
        </LinearGradient>
      </Pressable>
    );
  }

  const variantStyle: ViewStyle =
    variant === 'secondary'
      ? {
          borderWidth: 1.5,
          borderColor: theme.colors.primary,
          backgroundColor: 'transparent',
        }
      : { backgroundColor: 'transparent', height: 'auto' };

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      testID={testID}
      style={[base, variantStyle, style]}
    >
      {content}
    </Pressable>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  icon: { marginLeft: SPACING.xs },
});
