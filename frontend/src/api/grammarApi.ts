/** Grammar lessons API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import type { GrammarLessonDetail, GrammarLessonList } from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms));

const MOCK_LIST: GrammarLessonList = {
  items: [
    {
      id: 'g1',
      title: 'Subject-verb agreement',
      conceptTag: 'subject_verb_agreement',
      summary: 'Making the verb match its subject, even at a distance.',
      level: 'beginner',
      minutes: 6,
      recommended: true,
    },
    {
      id: 'g2',
      title: 'Complex sentences for a higher band',
      conceptTag: 'sentence_complexity',
      summary:
        'Combine ideas with subordinate clauses instead of short sentences.',
      level: 'intermediate',
      minutes: 8,
      recommended: false,
    },
    {
      id: 'g3',
      title: 'Articles: a, an and the',
      conceptTag: 'articles',
      summary: 'When to use a/an, the, or no article at all.',
      level: 'beginner',
      minutes: 5,
      recommended: false,
    },
  ],
  recommendedCount: 1,
};

const MOCK_DETAIL: GrammarLessonDetail = {
  id: 'g1',
  title: 'Subject-verb agreement',
  conceptTag: 'subject_verb_agreement',
  summary: 'Making the verb match its subject, even at a distance.',
  body:
    'A singular subject takes a singular verb, and a plural subject takes a ' +
    'plural verb. Watch for phrases between the subject and verb: the verb ' +
    'agrees with the subject, not with the nearest noun.',
  examples: [
    {
      incorrect: 'The number of students are increasing.',
      correct: 'The number of students is increasing.',
      note: "The subject is 'the number', which is singular.",
    },
  ],
  level: 'beginner',
  minutes: 6,
};

export const grammarApi = {
  async listLessons(tag?: string): Promise<GrammarLessonList> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return MOCK_LIST;
    }
    try {
      const { data } = await apiClient.get<GrammarLessonList>(
        ENDPOINTS.grammar.lessons,
        { params: tag ? { tag } : undefined },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getLesson(lessonId: string): Promise<GrammarLessonDetail> {
    if (API_CONFIG.useMock) {
      await delay(250);
      return { ...MOCK_DETAIL, id: lessonId };
    }
    try {
      const { data } = await apiClient.get<GrammarLessonDetail>(
        ENDPOINTS.grammar.lesson(lessonId),
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
