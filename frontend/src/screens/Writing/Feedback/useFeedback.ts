/** Writing feedback logic: loads feedback + manages draft/model tab. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { writingApi } from '../../../api';
import type {
  FeedbackTab,
  RootStackParamList,
  WritingFeedback,
} from '../../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;
type FeedbackRoute = RouteProp<RootStackParamList, 'WritingFeedback'>;

interface UseFeedbackResult {
  feedback: WritingFeedback | null;
  isLoading: boolean;
  activeTab: FeedbackTab;
  setTab: (tab: FeedbackTab) => void;
  onExport: () => void;
  onBack: () => void;
}

export const useFeedback = (): UseFeedbackResult => {
  const navigation = useNavigation<Nav>();
  const route = useRoute<FeedbackRoute>();
  const attemptId = route.params.attemptId;

  const [feedback, setFeedback] = useState<WritingFeedback | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<FeedbackTab>('draft');

  useEffect(() => {
    let mounted = true;
    const load = async (): Promise<void> => {
      const result = await writingApi.getFeedback(attemptId);
      if (mounted) {
        setFeedback(result);
        setIsLoading(false);
      }
    };
    void load();
    return () => {
      mounted = false;
    };
  }, [attemptId]);

  const setTab = useCallback((tab: FeedbackTab): void => {
    setActiveTab(tab);
  }, []);

  const onExport = useCallback((): void => {
    // TODO: wire to backend PDF export endpoint.
  }, []);

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return { feedback, isLoading, activeTab, setTab, onExport, onBack };
};
