import { expect, test } from 'vitest';
import { filterLogs } from './model';
import type { LogRecord } from './model';

const rows: LogRecord[] = [
  {
    id: '1',
    time: '12:00',
    process: 'App One',
    pid: '42',
    type: 'error',
    subsystem: 'org.sample',
    category: 'file',
    message: 'Permission denied',
    raw: '{}',
  },
  {
    id: '2',
    time: '12:01',
    process: 'Other',
    pid: '43',
    type: 'info',
    subsystem: 'org.sample',
    category: 'network',
    message: 'Connected',
    raw: '{}',
  },
];

test('property filters intersect while alternatives for the same property match either', () => {
  expect(
    filterLogs(rows, 'p:"app one" m:"permission denied" pid:42', 'all'),
  ).toEqual([rows[0]]);
  expect(filterLogs(rows, 'p:"app one" p:other s:org.sample', 'all')).toEqual(
    rows,
  );
  expect(filterLogs(rows, 'p:other t:error', 'all')).toEqual([]);
});

test('severity and free text narrow the retained messages without altering them', () => {
  expect(filterLogs(rows, '', 'errors')).toEqual([rows[0]]);
  expect(filterLogs(rows, 'connected', 'info')).toEqual([rows[1]]);
  expect(rows[0]?.message).toBe('Permission denied');
});
