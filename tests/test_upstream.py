#!/usr/bin/env python3
"""Offline updater contracts: native merges and fail-closed boundaries."""
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('upstream', Path(__file__).resolve().parents[1] / 'scripts/upstream.py')
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)


def baseline():
    return {'Agent.qml': b'alpha\nbeta\ngamma\ndelta\nepsilon\nzeta\n',
            'Main.qml': b'main\n', 'Panel.qml': b'panel\n', 'README.md': b'docs\n',
            'manifest.json': json.dumps({'schemaVersion': 1, 'id': 'omarchy.agents',
                                        'entryPoints': {'barWidget': 'Panel.qml'}}).encode()}


class UpstreamContracts(unittest.TestCase):
    def test_unchanged_stock_preserves_fork(self):
        base = baseline()
        ours = dict(base, **{'assets/pi.svg': b'<svg/>', 'Panel.qml': b'local panel\n'})
        self.assertEqual(upstream.merge(base, ours, base), ours)

    def test_disjoint_merge_preserves_both(self):
        base = baseline()
        ours = dict(base, **{'Agent.qml': base['Agent.qml'].replace(b'alpha', b'local')})
        theirs = dict(base, **{'Agent.qml': base['Agent.qml'].replace(b'zeta', b'upstream')})
        self.assertEqual(upstream.merge(base, ours, theirs)['Agent.qml'],
                         ours['Agent.qml'].replace(b'zeta', b'upstream'))

    def test_conflict_does_not_mutate_inputs(self):
        base = baseline()
        ours = dict(base, **{'Panel.qml': b'ours\n'})
        theirs = dict(base, **{'Panel.qml': b'theirs\n'})
        original = ours.copy()
        with self.assertRaisesRegex(ValueError, 'merge failed'):
            upstream.merge(base, ours, theirs)
        self.assertEqual(ours, original)

    def test_additions_deletions_and_local_assets(self):
        base = dict(baseline(), **{'assets/old.svg': b'old'})
        ours = dict(base, **{'assets/pi.svg': b'pi'})
        theirs = baseline()
        theirs['assets/new.svg'] = b'new'
        merged = upstream.merge(base, ours, theirs)
        self.assertNotIn('assets/old.svg', merged)
        self.assertEqual(merged['assets/new.svg'], b'new')
        self.assertEqual(merged['assets/pi.svg'], b'pi')

    def test_untrusted_paths_and_limits_refused(self):
        for name in ['../escape', 'assets/../../escape.svg', '.github/workflows/ci.yml',
                     'assets/nested/icon.svg', '-flag.svg', 'assets/link']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                upstream.validate(dict(baseline(), **{name: b'bad'}))
        with self.assertRaises(ValueError):
            upstream.validate(dict(baseline(), **{'Panel.qml': b'x' * (upstream.LIMIT + 1)}))

    def test_entrypoint_change_refused(self):
        files = baseline()
        files['manifest.json'] = b'{"schemaVersion":1,"id":"omarchy.agents","entryPoints":{"barWidget":"escape.qml"}}'
        with self.assertRaisesRegex(ValueError, 'entry-point'):
            upstream.validate(files)


if __name__ == '__main__':
    unittest.main()
