/** Welcome / value-proposition carousel (UI only). Logic in useWelcome. */

import React from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import {
  AppText,
  Button,
  Icon,
  Logo,
  ScreenContainer,
  useTheme,
} from '@components';
import { SPACING } from '@constants';
import { useWelcome } from './useWelcome';

export const Welcome: React.FC = () => {
  const theme = useTheme();
  const { slides, index, isLast, scrollRef, onScroll, onWidth, next, skip } =
    useWelcome();

  return (
    <ScreenContainer>
      <View
        style={styles.root}
        onLayout={event => onWidth(event.nativeEvent.layout.width)}
      >
        <View style={styles.header}>
          <Logo size={40} />
          <Pressable
            onPress={skip}
            accessibilityRole="button"
            testID="welcome-skip"
          >
            <AppText variant="labelMd" color="primary">
              Skip
            </AppText>
          </Pressable>
        </View>

        <ScrollView
          ref={scrollRef}
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          onMomentumScrollEnd={onScroll}
          scrollEventThrottle={16}
          style={styles.pager}
          testID="welcome-pager"
        >
          {slides.map(slide => (
            <View key={slide.title} style={styles.slideWrap}>
              <View style={styles.slide} testID={`welcome-slide-${slide.icon}`}>
                <View
                  style={[
                    styles.iconCircle,
                    { backgroundColor: theme.colors.primaryContainer },
                  ]}
                >
                  <Icon name={slide.icon} size={44} color="primary" />
                </View>
                <AppText
                  variant="headlineMd"
                  align="center"
                  style={styles.title}
                >
                  {slide.title}
                </AppText>
                <AppText variant="bodyMd" color="textSecondary" align="center">
                  {slide.body}
                </AppText>
              </View>
            </View>
          ))}
        </ScrollView>

        <View style={styles.dots} testID="welcome-dots">
          {slides.map((slide, i) => (
            <View
              key={slide.title}
              style={[
                styles.dot,
                {
                  width: i === index ? 22 : 8,
                  backgroundColor:
                    i === index
                      ? theme.colors.primary
                      : theme.colors.outlineVariant,
                },
              ]}
            />
          ))}
        </View>

        <Button
          title={isLast ? 'Get started' : 'Next'}
          onPress={next}
          testID="welcome-next"
        />
      </View>
    </ScreenContainer>
  );
};

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: SPACING.lg,
  },
  pager: { flex: 1 },
  // The pager measures the container, so each page must fill it exactly or the
  // slides drift out of alignment as you swipe.
  slideWrap: { width: '100%', flexGrow: 1 },
  slide: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  iconCircle: {
    width: 104,
    height: 104,
    borderRadius: 52,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: SPACING.lg,
  },
  title: { marginBottom: SPACING.sm },
  dots: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: SPACING.sm,
    marginVertical: SPACING.lg,
  },
  dot: { height: 8, borderRadius: 4 },
});
