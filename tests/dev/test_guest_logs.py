"""Parsing and source refusal do not require a Darwin guest."""

import json
import os
from pathlib import Path
import plistlib
import sys
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.simulator import guest_logs


class GuestLogTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'posix', 'guest process boundary is Linux-only')
    def test_guest_reader_enforces_output_limit_and_exit_status(self):
        import pwd
        user = pwd.getpwuid(os.getuid())
        start = subprocess.Popen
        for program, message in [('import sys; sys.stderr.write("denied"); sys.exit(1)', 'denied'),
                                 ('print("x" * 1100000)', 'exceeded 1 MiB')]:
            children = []

            def launch(command, **kwargs):
                self.assertEqual(command[:2], ['/usr/local/bin/darling', 'shell'])
                child = start([sys.executable, '-c', program], **kwargs)
                children.append(child)
                return child

            with patch.object(guest_logs.subprocess, 'Popen', side_effect=launch):
                with self.assertRaisesRegex(ValueError, message):
                    guest_logs.capture(guest_logs.SOURCES['asl'], user, Path(user.pw_dir))
            self.assertIsNotNone(children[0].poll())

    def test_asl_preserves_fields_and_reports_error_type(self):
        value = {'Time': '123', 'Sender': 'Example', 'PID': '42', 'Level': '3', 'Message': '<script>raw message</script>'}
        rows, truncated = guest_logs.records('asl', plistlib.dumps([value]))
        self.assertFalse(truncated)
        self.assertEqual(rows[0]['type'], 'error')
        self.assertEqual(rows[0]['message'], value['Message'])
        self.assertEqual(json.loads(rows[0]['raw']), value)

    def test_unified_fields_and_bounded_tail(self):
        value = {'timestamp': 'time', 'processImagePath': '/Applications/Example', 'processID': 42,
                 'messageType': 'Fault', 'subsystem': 'org.sample', 'category': 'file', 'eventMessage': 'failed'}
        rows, truncated = guest_logs.records('unified', json.dumps([value] * 501).encode())
        self.assertTrue(truncated)
        self.assertEqual(len(rows), 500)
        self.assertEqual(rows[0]['process'], 'Example')
        self.assertEqual(rows[0]['type'], 'fault')

    def test_missing_facility_is_unavailable_not_empty_success(self):
        with patch.object(guest_logs, 'capture', side_effect=ValueError('not implemented')):
            result = guest_logs.read('asl', None, Path('/guest'))
        self.assertFalse(result['available'])
        self.assertIn('not implemented', result['note'])
        with self.assertRaises(ValueError):
            guest_logs.read('../../host', None, Path('/guest'))

    def test_disabled_asl_daemon_does_not_report_empty_success(self):
        replies = [plistlib.dumps([]), plistlib.dumps({'Disabled': True}), ValueError('job not found')]
        with patch.object(guest_logs, 'capture', side_effect=replies):
            result = guest_logs.read('asl', None, Path('/guest'))
        self.assertFalse(result['available'])
        self.assertIn('syslogd is disabled', result['note'])

    def test_loaded_daemon_overrides_disabled_default_and_empty_query_is_unverified(self):
        replies = [plistlib.dumps([]), plistlib.dumps({'Disabled': True}), b'loaded job']
        with patch.object(guest_logs, 'capture', side_effect=replies):
            result = guest_logs.read('asl', None, Path('/guest'))
        self.assertTrue(result['available'])
        self.assertIn('ingestion has not been verified', result['note'])

    def test_plain_log_retains_original_lines_and_oversize_is_refused(self):
        rows, _ = guest_logs.records('system', b'first\nsecond\n')
        self.assertEqual([row['message'] for row in rows], ['first', 'second'])
        with self.assertRaises(ValueError):
            guest_logs.records('system', b'x' * (guest_logs.LIMIT + 1))


if __name__ == '__main__':
    unittest.main()
