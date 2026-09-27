import type { Command, Transport } from './protocol';

export class HttpTransport implements Transport {
  readonly kind = 'live';

  constructor(
    private readonly request: typeof fetch = (input, init) =>
      fetch(input, init),
  ) {}

  async authenticate(token: string): Promise<void> {
    if (!token) {
      return;
    }
    const response = await this.request('/v1/auth', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw new Error('Controller authentication failed.');
    }
  }

  async send(command: Command, signal?: AbortSignal): Promise<unknown> {
    const response = await this.request('/v1/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
      ...(signal ? { signal } : {}),
    });
    const value: unknown = await response.json();
    if (
      typeof value === 'object' &&
      value !== null &&
      'error' in value &&
      typeof value.error === 'string'
    ) {
      throw new Error(value.error);
    }
    if (!response.ok) {
      throw new Error(`Controller returned HTTP ${response.status}.`);
    }
    return value;
  }
}
