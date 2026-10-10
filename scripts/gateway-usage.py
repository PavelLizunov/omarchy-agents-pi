#!/usr/bin/python3 -I
"""Adapt the existing DSH limits collector to one Omarchy usage record."""
import argparse
import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

LIMIT = 65536


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def text(value, fallback=''):
    return value[:160] if isinstance(value, str) else fallback


def adapt(data):
    if not isinstance(data, dict) or not isinstance(data.get('accounts'), list) or not isinstance(data.get('groups'), list):
        raise ValueError('Invalid collector response')
    if len(data['accounts']) > 64 or len(data['groups']) > 32:
        raise ValueError('Collector response exceeds limits')
    accounts = []
    seen = set()
    for raw in data['accounts']:
        if not isinstance(raw, dict) or raw.get('provider') not in ('antigravity', 'codex', 'xai'):
            raise ValueError('Invalid account')
        identity = (raw['provider'], text(raw.get('authIndex')))
        if not identity[1] or identity in seen:
            raise ValueError('Invalid account identity')
        seen.add(identity)
        windows = []
        if not isinstance(raw.get('windows'), list) or len(raw['windows']) > 16:
            raise ValueError('Invalid account windows')
        for window in raw['windows']:
            if not isinstance(window, dict):
                raise ValueError('Invalid account window')
            remaining = window.get('remainingPercent')
            windows.append({'key': text(window.get('key')), 'label': text(window.get('label'), 'Limit'),
                            'remainingPercent': remaining if finite(remaining) and 0 <= remaining <= 100 else None,
                            'resetsAt': text(window.get('resetsAt'))})
        accounts.append({'provider': raw['provider'], 'authIndex': identity[1],
                         'account': text(raw.get('account')), 'plan': text(raw.get('plan')),
                         'status': text(raw.get('status'), 'unknown'), 'windows': windows})
    pools = []
    for group in data['groups']:
        if not isinstance(group, dict):
            raise ValueError('Invalid pool')
        total, available = group.get('total'), group.get('available')
        if not finite(total) or not finite(available) or total <= 0 or not 0 <= available <= total:
            raise ValueError('Invalid pool capacity')
        pools.append({'key': text(group.get('key')), 'model': text(group.get('model')),
                      'label': text(group.get('label'), 'Antigravity'), 'plan': text(group.get('plan')),
                      'total': total, 'available': available, 'resetsAt': text(group.get('resetsAt'))})
    errors = sum(a['status'] == 'error' for a in accounts)
    disabled = sum(a['status'] == 'disabled' for a in accounts)
    return {'schemaVersion': 1, 'id': 'gateway', 'name': 'AI Gateway', 'ready': True,
            'tierLabel': 'Subscription limits', 'updatedAt': text(data.get('updatedAt')),
            'limits': [], 'gateway': {'accounts': accounts, 'pools': pools, 'errors': errors, 'disabled': disabled},
            'hasLocalStats': False, 'hasPromptStats': False}


def collect(config):
    host = config.get('sshHost', '')
    if not isinstance(host, str) or not re.fullmatch(r'[A-Za-z0-9_.@-]{1,128}', host) or host.startswith('-'):
        raise ValueError('Invalid SSH host')
    for key in ('collectorPath', 'secretFile'):
        if not isinstance(config.get(key), str) or not config[key].startswith('/') or len(config[key]) > 512:
            raise ValueError('Invalid remote path')
    payload = json.dumps({k: config[k] for k in ('collectorPath', 'secretFile', 'gatewayUrl')})
    user = config.get('remoteUser', 'dsh')
    if not re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}', user):
        raise ValueError('Invalid remote user')
    command = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=yes',
               '-o', 'ConnectionAttempts=1', host,
               'sudo -n -u ' + shlex.quote(user) + ' /usr/bin/timeout --kill-after=2s 50s /usr/local/bin/node --input-type=module - ' + shlex.quote(payload)]
    # The remote producer bounds stdout before emission; stderr is not exposed.
    result = subprocess.run(command, input=Path(__file__).with_name('gateway-limits.mjs').read_text(),
                            capture_output=True, text=True, timeout=58)
    if result.returncode or len(result.stdout.encode()) > LIMIT:
        raise ValueError('Gateway collector failed')
    return adapt(json.loads(result.stdout))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path.home() / '.config/omarchy/agents/gateway.json')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--limits-only', action='store_true')
    args = parser.parse_args()
    state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'omarchy/agents/usage'
    cached = state / 'gateway.json'
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/run/user/' + str(os.getuid())))
    lock_path = runtime / 'slovn-agents-gateway.lock'
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        lock = os.fdopen(fd, 'r+')
        if os.fstat(fd).st_uid != os.getuid() or os.fstat(fd).st_mode & 0o077:
            return 1
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 1
    try:
        if not args.force and cached.is_file() and cached.stat().st_size <= LIMIT:
            previous = json.loads(cached.read_text())
            timestamp = datetime.datetime.fromisoformat(previous.get('updatedAt', '').replace('Z', '+00:00'))
            age = (datetime.datetime.now(datetime.timezone.utc) - timestamp).total_seconds()
            if previous.get('id') == 'gateway' and previous.get('ready') is True and 0 <= age < 60:
                print(json.dumps(previous))
                return 0
    except (OSError, ValueError, TypeError):
        pass
    try:
        config = json.loads(args.config.read_text())
        record = collect(config)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        record = {'schemaVersion': 1, 'id': 'gateway', 'name': 'AI Gateway', 'ready': False,
                  'tierLabel': 'Subscription limits', 'limits': [], 'hasLocalStats': False, 'hasPromptStats': False,
                  'gateway': {'accounts': [], 'pools': [], 'errors': 0, 'disabled': 0},
                  'usageStatusText': 'Gateway limits unavailable',
                  'authHelpText': 'Could not read subscription limits from the configured DSH host.'}
    output = json.dumps(record)
    if len(output.encode()) > LIMIT:
        return 1
    print(output)
    return 0


if __name__ == '__main__':
    sys.exit(main())
