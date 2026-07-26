/** Attempt history logic: per-module paginated history with module switching. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import {
  listeningApi,
  readingApi,
  speakingApi,
  writingApi,
} from '../../api';
import type { Band, IeltsModule, RootStackParamList } from '../../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

/** Normalized row so one list can render every module's history. */
export interface HistoryRow {
  attemptId: string;
  band: Band | null;
  detail: string;
  createdAt: string;
  status: string | null;
}

interface UseHistoryResult {
  module: IeltsModule;
  rows: HistoryRow[];
  isLoading: boolean;
  isLoadingMore: boolean;
  hasMore: boolean;
  error: string | null;
  setModule: (module: IeltsModule) => void;
  loadMore: () => void;
  onBack: () => void;
}

interface Page {
  rows: HistoryRow[];
  nextCursor: string | null;
}

async function fetchPage(
  module: IeltsModule,
  cursor?: string,
): Promise<Page> {
  switch (module) {
    case 'writing': {
      const page = await writingApi.getHistory(cursor);
      return {
        nextCursor: page.nextCursor,
        rows: page.items.map((item) => ({
          attemptId: item.attemptId,
          band: item.overallBand,
          detail: `Task ${item.taskType} · ${item.wordCount} words`,
          createdAt: item.createdAt,
          status: item.status,
        })),
      };
    }
    case 'speaking': {
      const page = await speakingApi.getHistory(cursor);
      return {
        nextCursor: page.nextCursor,
        rows: page.items.map((item) => ({
          attemptId: item.attemptId,
          band: item.overallBand,
          detail: item.part ? `Part ${item.part}` : 'Speaking',
          createdAt: item.createdAt,
          status: item.status,
        })),
      };
    }
    case 'reading': {
      const page = await readingApi.getHistory(cursor);
      return {
        nextCursor: page.nextCursor,
        rows: page.items.map((item) => ({
          attemptId: item.attemptId,
          band: item.band,
          detail: `${item.rawScore}/${item.totalQuestions} correct`,
          createdAt: item.createdAt,
          status: null,
        })),
      };
    }
    case 'listening': {
      const page = await listeningApi.getHistory(cursor);
      return {
        nextCursor: page.nextCursor,
        rows: page.items.map((item) => ({
          attemptId: item.attemptId,
          band: item.band,
          detail: `${item.rawScore}/${item.totalQuestions} correct`,
          createdAt: item.createdAt,
          status: null,
        })),
      };
    }
  }
}

export const useHistory = (initial: IeltsModule = 'writing'): UseHistoryResult => {
  const navigation = useNavigation<Nav>();
  const [module, setModuleState] = useState<IeltsModule>(initial);
  const [rows, setRows] = useState<HistoryRow[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (target: IeltsModule): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const page = await fetchPage(target);
      setRows(page.rows);
      setCursor(page.nextCursor);
    } catch {
      setError('Could not load your history.');
      setRows([]);
      setCursor(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(module);
  }, [load, module]);

  const setModule = useCallback((next: IeltsModule): void => {
    setModuleState(next);
  }, []);

  const loadMore = useCallback((): void => {
    if (!cursor || isLoadingMore) {
      return;
    }
    setIsLoadingMore(true);
    fetchPage(module, cursor)
      .then((page) => {
        setRows((prev) => [...prev, ...page.rows]);
        setCursor(page.nextCursor);
      })
      .catch(() => setError('Could not load more attempts.'))
      .finally(() => setIsLoadingMore(false));
  }, [cursor, isLoadingMore, module]);

  const onBack = useCallback((): void => {
    navigation.goBack();
  }, [navigation]);

  return {
    module,
    rows,
    isLoading,
    isLoadingMore,
    hasMore: cursor !== null,
    error,
    setModule,
    loadMore,
    onBack,
  };
};
