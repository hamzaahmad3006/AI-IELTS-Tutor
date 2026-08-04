/** Study plan logic: load, generate, and tick tasks off. */

import { useCallback, useEffect, useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { plannerApi } from '@api';
import { enqueue, showToast, useAppDispatch } from '@redux';
import type { PlanTask, RootStackParamList, StudyPlan } from '@models';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface UsePlanResult {
  plan: StudyPlan | null;
  isLoading: boolean;
  isGenerating: boolean;
  error: string | null;
  weeks: number[];
  activeWeek: number;
  setActiveWeek: (week: number) => void;
  tasksForWeek: PlanTask[];
  generate: () => void;
  toggleTask: (task: PlanTask) => void;
  onBack: () => void;
}

export const usePlan = (): UsePlanResult => {
  const navigation = useNavigation<Nav>();
  const dispatch = useAppDispatch();
  const [plan, setPlan] = useState<StudyPlan | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeWeek, setActiveWeek] = useState<number>(1);

  useEffect(() => {
    let active = true;
    plannerApi
      .getPlan()
      .then(data => {
        if (active) {
          setPlan(data);
        }
      })
      .catch(() => {
        if (active) {
          setError('Could not load your study plan.');
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
  }, []);

  const generate = useCallback((): void => {
    setIsGenerating(true);
    setError(null);
    plannerApi
      .generate()
      .then(data => {
        setPlan(data);
        setActiveWeek(1);
        dispatch(showToast({ message: 'Study plan ready.', tone: 'success' }));
      })
      .catch(() =>
        setError('Could not build a plan. Complete onboarding first.'),
      )
      .finally(() => setIsGenerating(false));
  }, [dispatch]);

  const toggleTask = useCallback(
    (task: PlanTask): void => {
      const next = !task.isDone;
      // Optimistic: ticking a task must feel instant. The request still runs,
      // and a failure rolls the tick back rather than leaving a lie on screen.
      setPlan(current =>
        current
          ? {
              ...current,
              tasks: current.tasks.map(t =>
                t.id === task.id ? { ...t, isDone: next } : t,
              ),
              completedCount: current.completedCount + (next ? 1 : -1),
            }
          : current,
      );
      plannerApi.setTaskDone(task.id, next).catch(sendError => {
        // A request that never reached the server is not a failed edit, it is
        // an unsent one. Queue it and keep the tick, rather than rolling back
        // work the learner did and making them do it again.
        const unreachable =
          typeof sendError === 'object' &&
          sendError !== null &&
          (sendError as { status?: number }).status === 0;

        if (unreachable) {
          dispatch(
            enqueue({
              kind: 'planTask',
              targetId: task.id,
              payload: { isDone: next },
            }),
          );
          return;
        }

        setPlan(current =>
          current
            ? {
                ...current,
                tasks: current.tasks.map(t =>
                  t.id === task.id ? { ...t, isDone: task.isDone } : t,
                ),
                completedCount: current.completedCount + (next ? -1 : 1),
              }
            : current,
        );
        dispatch(
          showToast({ message: 'Could not save that change.', tone: 'error' }),
        );
      });
    },
    [dispatch],
  );

  const weeks = plan
    ? Array.from({ length: plan.weeks }, (_, index) => index + 1)
    : [];

  return {
    plan,
    isLoading,
    isGenerating,
    error,
    weeks,
    activeWeek,
    setActiveWeek,
    tasksForWeek: (plan?.tasks ?? []).filter(t => t.week === activeWeek),
    generate,
    toggleTask,
    onBack: () => navigation.goBack(),
  };
};
