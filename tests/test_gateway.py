#!/usr/bin/env python3
"""Offline gateway normalization checks; no network or credentials."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('gateway', Path(__file__).resolve().parents[1] / 'scripts/gateway-usage.py')
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class GatewayTest(unittest.TestCase):
    def data(self):
        return {'accounts': [{'provider': 'codex', 'authIndex': '1', 'account': 'codex 1', 'plan': 'pro',
                              'status': 'available', 'windows': [{'label': 'Weekly', 'remainingPercent': 0}]}],
                'groups': [{'label': 'Gemini Weekly', 'plan': 'pro', 'total': 2, 'available': 1.25}]}

    def test_zero_unknown_and_pool(self):
        data = self.data()
        data['accounts'][0]['windows'] += [{'label': 'Unknown', 'remainingPercent': None}, {'label': 'Invalid', 'remainingPercent': True}]
        result = gateway.adapt(data)
        self.assertEqual(result['gateway']['accounts'][0]['windows'][0]['remainingPercent'], 0)
        self.assertIsNone(result['gateway']['accounts'][0]['windows'][1]['remainingPercent'])
        self.assertIsNone(result['gateway']['accounts'][0]['windows'][2]['remainingPercent'])
        self.assertEqual(result['gateway']['pools'][0]['available'], 1.25)
        self.assertEqual(result['id'], 'gateway')
        self.assertEqual(result['limits'], [])

    def test_invalid_pool_and_identity(self):
        for bad in [None, True, -1, 3, float('nan')]:
            data = self.data(); data['groups'][0]['available'] = bad
            with self.assertRaises(ValueError): gateway.adapt(data)
        data = self.data(); data['accounts'] *= 2
        with self.assertRaises(ValueError): gateway.adapt(data)

    def test_error_disabled_and_provider_identity(self):
        data = self.data()
        data['accounts'] += [{'provider': 'antigravity', 'authIndex': '1', 'status': 'disabled', 'windows': []},
                             {'provider': 'antigravity', 'authIndex': '2', 'status': 'error', 'windows': []}]
        result = gateway.adapt(data)['gateway']
        self.assertEqual(result['errors'], 1)
        self.assertEqual(result['disabled'], 1)
        self.assertEqual(len(result['accounts']), 3)


if __name__ == '__main__':
    unittest.main()
