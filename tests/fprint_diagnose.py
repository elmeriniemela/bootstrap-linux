#!/usr/bin/env python3
"""Behavior tests for files/fprint-diagnose using command stubs."""

import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / 'files' / 'fprint-diagnose'


class FprintDiagnoseTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.bin_dir = Path(self.tempdir.name) / 'bin'
        self.bin_dir.mkdir()
        self.counter = Path(self.tempdir.name) / 'counter'
        self.counter.write_text('0')

        self._stub('fprintd-list', '''
            #!/bin/bash
            if [[ ${FPRINT_LIST_FAIL:-0} == 1 ]]; then
                echo 'device unavailable' >&2
                exit 1
            fi
            echo 'found 1 devices'
            echo 'Fingerprints for user tester on Goodix MOC Fingerprint Sensor (press):'
            if [[ ${FPRINT_NO_ENROLLMENT:-0} != 1 ]]; then
                echo ' - #0: right-index-finger'
            fi
        ''')
        self._stub('fprintd-verify', '''
            #!/bin/bash
            count=$(<"$FPRINT_COUNTER")
            count=$((count + 1))
            printf '%d' "$count" >"$FPRINT_COUNTER"
            IFS=, read -ra results <<<"$FPRINT_RESULTS"
            result=${results[count - 1]}
            case $result in
                match)
                    echo 'Verify result: verify-match (done)'
                    exit 0
                    ;;
                no-match)
                    echo 'Verify result: verify-no-match (done)'
                    exit 1
                    ;;
                timeout)
                    exit 124
                    ;;
                *)
                    echo 'D-Bus device error' >&2
                    exit 2
                    ;;
            esac
        ''')
        self._stub('pacman', '''
            #!/bin/bash
            echo 'fprintd 1.94.5-2'
            echo 'libfprint 1.94.100-1'
        ''')
        self._stub('journalctl', '''
            #!/bin/bash
            if [[ ${FPRINT_JOURNAL_FAIL:-0} == 1 ]]; then
                exit 1
            fi
            cat <<'EOF'
Capture sample poor quality(15): 57 or coverage(65): 64
Capture sample poor quality(60): 57 or coverage(65): 70
Sample overlapping ratio is too High(80): 84
Capture sample failed, result: 0xc0
report_verify_status: result verify-match
report_verify_status: result verify-no-match
EOF
        ''')

    def tearDown(self):
        self.tempdir.cleanup()

    def _stub(self, name, body):
        path = self.bin_dir / name
        path.write_text(textwrap.dedent(body).lstrip())
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _run(self, *args, results='match', input_text=None, **extra_env):
        env = os.environ.copy()
        env.update({
            'PATH': f'{self.bin_dir}:{env["PATH"]}',
            'USER': 'tester',
            'FPRINT_COUNTER': str(self.counter),
            'FPRINT_RESULTS': results,
        })
        env.update(extra_env)
        if input_text is None:
            count = int(args[0]) if args and str(args[0]).isdigit() else 10
            input_text = '\n' * count
        return subprocess.run(
            [str(SCRIPT), *(str(arg) for arg in args)],
            input=input_text,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_mixed_results_and_journal_summary(self):
        result = self._run(4, results='match,no-match,timeout,error')
        self.assertEqual(result.returncode, 1)
        self.assertIn('matches:       1/4 (25.0%)', result.stdout)
        self.assertIn('no-matches:    1', result.stdout)
        self.assertIn('timeouts:      1', result.stdout)
        self.assertIn('other errors:  1', result.stdout)
        self.assertIn('below quality threshold:    1', result.stdout)
        self.assertIn('below coverage threshold:   1', result.stdout)
        self.assertIn('verification scan results:    1 match, 1 no-match', result.stdout)
        self.assertIn('D-Bus device error', result.stderr)

    def test_expected_results_complete_successfully(self):
        result = self._run(3, results='match,no-match,timeout')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('matches:       1/3 (33.3%)', result.stdout)

    def test_rejects_invalid_attempt_count(self):
        for value in ('0', '101', 'abc'):
            with self.subTest(value=value):
                result = self._run(value, input_text='')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ATTEMPTS must be an integer', result.stderr)

    def test_missing_enrollment_is_fatal(self):
        result = self._run(1, input_text='', FPRINT_NO_ENROLLMENT='1')
        self.assertEqual(result.returncode, 1)
        self.assertIn('no enrolled fingerprints found', result.stderr)

    def test_unreadable_journal_does_not_fail_verification_test(self):
        result = self._run(1, FPRINT_JOURNAL_FAIL='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('journal could not be read', result.stdout)


if __name__ == '__main__':
    unittest.main()
