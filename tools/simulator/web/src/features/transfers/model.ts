import { z } from 'zod';

export const TRANSFER_LIMIT = 64 * 1024 * 1024;
export const CHUNK_SIZE = 262144;

export const exportSchema = z.object({
  size: z.number().int().min(0).max(TRANSFER_LIMIT),
  offset: z.number().int().nonnegative(),
  sha256: z.string().regex(/^[a-f0-9]{64}$/),
  data: z.string(),
});

export function transferPath(value: string): string {
  if (
    !value ||
    value.includes('\\') ||
    value.split('/').some((part) => !part || part === '.' || part === '..')
  ) {
    throw new Error('Use a path relative to the guest Imports directory.');
  }
  return value;
}
