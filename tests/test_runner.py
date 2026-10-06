#!/usr/bin/env python3
"""Offline negative controls for fixture and output-path guards; no Qt process."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('agents_runner', Path(__file__).with_name('run.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerGuards(unittest.TestCase):
    def test_output_inside_source_refused(self):
        with self.assertRaisesRegex(ValueError, 'outside project'):
            runner.prepare(runner.ROOT / 'test-output')

    def test_output_inside_installed_refused(self):
        with self.assertRaisesRegex(ValueError, 'outside project'):
            runner.prepare(Path.home() / '.config/omarchy/plugins/test-output')

    def test_fixture_tamper_refused(self):
        with tempfile.TemporaryDirectory() as scratch:
            fixture = Path(scratch) / 'fixture'
            shutil.copytree(runner.FIXTURE, fixture)
            lock = json.loads((fixture / 'imports-lock.json').read_text())
            target = fixture / 'imports' / next(iter(lock))
            target.write_text(target.read_text() + '\n')
            original = runner.FIXTURE
            try:
                runner.FIXTURE = fixture
                with self.assertRaisesRegex(ValueError, 'lock mismatch'):
                    runner.prepare(Path(scratch) / 'output')
            finally:
                runner.FIXTURE = original

    def test_fixture_symlink_refused(self):
        with tempfile.TemporaryDirectory() as scratch:
            fixture = Path(scratch) / 'fixture'
            shutil.copytree(runner.FIXTURE, fixture)
            (fixture / 'link').symlink_to(fixture / 'tst_panel.qml')
            original = runner.FIXTURE
            try:
                runner.FIXTURE = fixture
                with self.assertRaisesRegex(ValueError, 'symlink'):
                    runner.prepare(Path(scratch) / 'output')
            finally:
                runner.FIXTURE = original


if __name__ == '__main__':
    unittest.main()
