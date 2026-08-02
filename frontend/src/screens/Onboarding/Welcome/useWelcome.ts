/** Welcome carousel logic: slide paging and entry into the numbered steps. */

import { useCallback, useRef, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { NativeScrollEvent, NativeSyntheticEvent } from 'react-native';
import { ScrollView } from 'react-native';
import type { IconName } from '../../../constants';
import type { OnboardingStackParamList } from '../../../types';

type Nav = NativeStackNavigationProp<OnboardingStackParamList>;

export interface WelcomeSlide {
  icon: IconName;
  title: string;
  body: string;
}

/**
 * Claims are deliberately limited to what the app actually does today: real
 * AI band scoring, weakness tracking that drives what you practise next, and
 * progress derived from your own attempts. Promising a guaranteed band, or
 * features that do not exist yet, would be a lie the product has to live with.
 */
export const SLIDES: WelcomeSlide[] = [
  {
    icon: 'sparkle',
    title: 'Scored like the real thing',
    body: 'Write or speak, and an AI examiner marks you against the four official IELTS criteria — with the reasoning, not just a number.',
  },
  {
    icon: 'practice',
    title: 'Practice that follows your weak spots',
    body: 'Every mistake is recorded by skill. Your next session leans on what you keep getting wrong instead of repeating what you already know.',
  },
  {
    icon: 'progress',
    title: 'See whether you are actually improving',
    body: 'Band trends, module balance and a predicted score, all built from your own attempts. No invented numbers.',
  },
];

interface UseWelcomeResult {
  slides: WelcomeSlide[];
  index: number;
  isLast: boolean;
  scrollRef: React.RefObject<ScrollView | null>;
  onScroll: (event: NativeSyntheticEvent<NativeScrollEvent>) => void;
  onWidth: (width: number) => void;
  next: () => void;
  skip: () => void;
}

export const useWelcome = (): UseWelcomeResult => {
  const navigation = useNavigation<Nav>();
  const scrollRef = useRef<ScrollView | null>(null);
  const [index, setIndex] = useState<number>(0);
  const [width, setWidth] = useState<number>(0);

  const onScroll = useCallback(
    (event: NativeSyntheticEvent<NativeScrollEvent>): void => {
      const page = width
        ? Math.round(event.nativeEvent.contentOffset.x / width)
        : 0;
      setIndex(Math.max(0, Math.min(SLIDES.length - 1, page)));
    },
    [width],
  );

  const start = useCallback((): void => {
    // Replace rather than push: the carousel is an intro, and swiping back to
    // it from the first real step would be confusing.
    //
    // The placement test comes first so the target band step can be framed
    // against a real starting point; it is skippable from there.
    navigation.replace('Diagnostic');
  }, [navigation]);

  const next = useCallback((): void => {
    if (index >= SLIDES.length - 1) {
      start();
      return;
    }
    const target = index + 1;
    setIndex(target);
    scrollRef.current?.scrollTo({ x: target * width, animated: true });
  }, [index, width, start]);

  return {
    slides: SLIDES,
    index,
    isLast: index === SLIDES.length - 1,
    scrollRef,
    onScroll,
    onWidth: setWidth,
    next,
    skip: start,
  };
};
