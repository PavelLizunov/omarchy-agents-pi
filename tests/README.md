# Isolated verification

Run from the source checkout, not the installed plugin directory:

```sh
python3 -B tests/check.py
python3 -B tests/test_runner.py
python3 -B tests/test_upstream.py
python3 -B tests/run.py
```

Requires Python 3 and Qt 6 Quick Test with QtQuick, QtQuick.Controls,
QtQuick.Shapes, QtTest and SVG image support. The default executable is
`/usr/lib/qt6/bin/qmltestrunner`; use `--qmltestrunner PATH` on other systems.
No packages are installed automatically.

Each invocation creates a new private directory outside the project, prints
its path and preserves logs, hashes, environment details and PNGs. Use
`--output-parent PATH` to select an external task-owned parent. It never
reuses existing evidence filenames. Remove retained runs manually when no
longer needed; the runner does not delete them.

## Contracts

The runner copies the current project QML and assets, without rewriting the
consumer, into an isolated fixture. Default checks cover valid and invalid
cache percentages, Pi priority without reordering other providers, provider
disabling, selection, left-click toggling, middle-click cycling, four rendered
states and label clipping. Each test receives a new panel instance. The stdlib guard checks verify
fixture-tamper and symlink rejection and refuse evidence paths inside source
or installed plugin directories. They launch no Qt process.

Focused inherited icon-race regression (also included in the default suite):

```sh
python3 -B tests/run.py --known-bug
```

Before the local correction, fast switching through a missing provider icon
left the valid Pi icon with an empty source. The regression now checks recovery
and captures the recovered state. A separate test retains same-provider fallback
from a missing asset to a valid one. The legacy option name is preserved; failures
are never converted to success. These tests do not reproduce the earlier shared
right-bar click outage. Compositor and qml-preview acceptance remain unverified.

## Fixture provenance and limits

`offscreen/imports` is a minimal dependency closure copied from the existing
local integration fixture. Its host controls retain their original comments
and layout. `imports-lock.json` pins every file; the runner refuses changed,
extra or symlinked dependencies until the lock is deliberately reviewed.
These fixtures are not deployed plugin code and are not cleaned as fork-owned
runtime code. Seventeen host QML/JS files were verified byte-for-byte against
Omarchy v4.0.4; popup/lifecycle adapters and restricted registrations are
intentional local reductions. See [provenance and licensing](../docs/PROVENANCE.md).
The original historical fixture is left untouched. The root MIT license covers
the published derivative controls and local inert adapters.

Process and FileView adapters perform no process launch, real reads or writes.
Detached execution and FileView writes throw. IPC is inert. HOME is synthetic;
the subprocess environment omits desktop sockets, credentials and provider
settings. Qt runs offscreen using software rendering, locale C.UTF-8 and DPR 1.
Font availability remains a machine dependency.

KeyboardPanel is adapted to an Item. These checks do not certify popup
placement, Hyprland focus, accessibility, host Bar.qml click routing, collector
correctness, network behavior or the live desktop. PNG inspection, interaction
checks, native design review and qml-preview MCP acceptance are separate gates.
No qml-preview MCP acceptance or independent review is claimed here.
