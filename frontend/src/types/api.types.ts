/** Generic API envelope & error types. */

export interface ApiSuccess<T> {
  data: T;
  correlationId: string;
}

export interface ApiFieldError {
  field: string;
  message: string;
}

export interface ApiProblem {
  type: string;
  title: string;
  status: number;
  code: string;
  correlationId: string;
  errors?: ApiFieldError[];
}

export interface PaginatedResult<T> {
  items: T[];
  nextCursor: string | null;
}

export type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
