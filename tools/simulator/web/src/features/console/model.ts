import { z } from 'zod';

export const logRecord = z.object({
  id: z.string(),
  time: z.string(),
  process: z.string(),
  pid: z.string(),
  type: z.string(),
  subsystem: z.string(),
  category: z.string(),
  message: z.string(),
  raw: z.string(),
});
export const logsSchema = z.object({
  source: z.string(),
  available: z.boolean(),
  records: z.array(logRecord),
  truncated: z.boolean(),
  note: z.string(),
});
export type LogRecord = z.infer<typeof logRecord>;

const aliases: Record<string, keyof LogRecord | 'any'> = {
  p: 'process',
  process: 'process',
  m: 'message',
  message: 'message',
  t: 'type',
  type: 'type',
  s: 'subsystem',
  subsystem: 'subsystem',
  c: 'category',
  category: 'category',
  pid: 'pid',
  any: 'any',
};

// Console-style search: alternatives within a property, intersection across properties.
export function filterLogs(
  rows: LogRecord[],
  query: string,
  severity: string,
): LogRecord[] {
  const groups = new Map<string, string[]>();
  const tokens = query.match(/(?:[^\s"]+|"[^"]*")+/g) ?? [];
  for (const token of tokens) {
    const colon = token.indexOf(':');
    const property =
      colon > 0 ? aliases[token.slice(0, colon).toLowerCase()] : undefined;
    const key = property ?? 'any';
    const value = (property ? token.slice(colon + 1) : token)
      .replace(/"/g, '')
      .toLowerCase();
    groups.set(key, [...(groups.get(key) ?? []), value]);
  }
  return rows.filter((row) => {
    if (severity === 'errors' && !['error', 'fault'].includes(row.type)) {
      return false;
    }
    if (severity !== 'all' && severity !== 'errors' && row.type !== severity) {
      return false;
    }
    for (const [key, terms] of groups) {
      const text =
        key === 'any'
          ? [
              row.time,
              row.process,
              row.pid,
              row.type,
              row.subsystem,
              row.category,
              row.message,
            ].join(' ')
          : row[key as keyof LogRecord];
      if (!terms.some((term) => text.toLowerCase().includes(term))) {
        return false;
      }
    }
    return true;
  });
}
