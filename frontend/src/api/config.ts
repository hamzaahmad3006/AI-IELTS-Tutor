/** API configuration. Swap BASE_URL per environment / build flavor. */

export const API_CONFIG = {
  baseUrl: 'http://10.0.2.2:8000/v1', // Android emulator -> host FastAPI
  timeoutMs: 30000,
  version: 'v1',
  /**
   * When true, API modules return typed local fixtures instead of hitting the
   * backend. Flip to false once the FastAPI backend is running.
   */
  useMock: true,
} as const;
