/** Part 1 / Part 3 runner: work through a themed question set, then score it. */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigation, useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { speakingApi } from '@api';
import type {
  RootStackParamList,
  SpeakingPart,
  SpeakingQuestionSet,
  SpeakingResult,
} from '@models';

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, 'SpeakingParts'>;

/** Minimum words per answer before the run can be scored. */
const MIN_WORDS_PER_ANSWER = 8;

const countWords = (text: string): number => {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
};

interface UseSpeakingPartsResult {
  part: SpeakingPart;
  isFullInterview: boolean;
  set: SpeakingQuestionSet | null;
  isLoading: boolean;
  index: number;
  answers: Record<string, string>;
  currentAnswer: string;
  wordCount: number;
  canAdvance: boolean;
  isLastQuestion: boolean;
  answeredCount: number;
  isSubmitting: boolean;
  result: SpeakingResult | null;
  error: string | null;
  setAnswer: (text: string) => void;
  goTo: (index: number) => void;
  nextQuestion: () => void;
  submit: () => void;
  onBack: () => void;
  continueAfterResult: () => void;
}

export const useSpeakingParts = (): UseSpeakingPartsResult => {
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const part: SpeakingPart = route.params?.part ?? 1;
  const isFullInterview = route.params?.full ?? false;

  const [set, setSet] = useState<SpeakingQuestionSet | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [index, setIndex] = useState<number>(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<SpeakingResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setIndex(0);
    setAnswers({});
    setResult(null);
    speakingApi
      .getQuestionSet(part)
      .then(data => {
        if (active) {
          setSet(data);
        }
      })
      .catch(() => {
        if (active) {
          setError('Could not load questions. Please try again.');
        }
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [part]);

  // Memoised because `?? []` would allocate a fresh array on every render,
  // which silently defeats the useMemo below.
  const questions = useMemo(() => set?.questions ?? [], [set]);
  const current = questions[index];
  const currentAnswer = current ? answers[current.id] ?? '' : '';
  const wordCount = countWords(currentAnswer);

  const answeredCount = useMemo(
    () =>
      questions.filter(
        q => countWords(answers[q.id] ?? '') >= MIN_WORDS_PER_ANSWER,
      ).length,
    [questions, answers],
  );

  const setAnswer = useCallback(
    (text: string): void => {
      if (!current) {
        return;
      }
      setAnswers(previous => ({ ...previous, [current.id]: text }));
    },
    [current],
  );

  const submit = useCallback((): void => {
    if (!set) {
      return;
    }
    setIsSubmitting(true);
    setError(null);
    // The run is scored as one response: an examiner marks the exchange, not
    // each answer in isolation, and four separately-scored fragments would not
    // produce a meaningful band.
    const transcript = set.questions
      .map((q, i) => `Q${i + 1}: ${q.question}\nA: ${answers[q.id] ?? ''}`)
      .join('\n\n');

    speakingApi
      .submit({ transcript, part: set.part, durationSec: 0 })
      .then(res => setResult(res))
      .catch(() => setError('Scoring failed. Please try again.'))
      .finally(() => setIsSubmitting(false));
  }, [set, answers]);

  const isLastQuestion = index >= questions.length - 1;

  const nextQuestion = useCallback((): void => {
    if (!isLastQuestion) {
      setIndex(i => i + 1);
    }
  }, [isLastQuestion]);

  const continueAfterResult = useCallback((): void => {
    // In a full interview Part 1 hands over to the cue card, which then hands
    // on to Part 3; a single-part session simply ends.
    if (isFullInterview && part === 1) {
      navigation.replace('SpeakingPractice');
      return;
    }
    navigation.goBack();
  }, [isFullInterview, part, navigation]);

  return {
    part,
    isFullInterview,
    set,
    isLoading,
    index,
    answers,
    currentAnswer,
    wordCount,
    canAdvance: wordCount >= MIN_WORDS_PER_ANSWER,
    isLastQuestion,
    answeredCount,
    isSubmitting,
    result,
    error,
    setAnswer,
    goTo: setIndex,
    nextQuestion,
    submit,
    onBack: () => navigation.goBack(),
    continueAfterResult,
  };
};
