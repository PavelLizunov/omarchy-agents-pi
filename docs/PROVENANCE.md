# Provenance and redistribution

## Upstream

The original plugin is `shell/plugins/agents` in
[omacom/omarchy](https://github.com/omacom/omarchy/tree/v4.0.4/shell/plugins/agents),
licensed MIT. The root LICENSE reproduces Omarchy's license and David Heinemeier
Hansson copyright notice from commit
`c668141e9c42b13c80c9ca4ea108e11708c5e8a5` (stable `v4.0.4`). All nine upstream
Agents files in `.upstream/agents` were verified byte-for-byte against that
release. The original historical fork point remains unknown.

The clone adds Pi-first ordering, Pi icon/cache presentation and clone metadata,
and corrects a stale deferred image-fallback callback. Local source, tests and
update automation are published under the same MIT license; upstream copyright
and meaningful original comments are preserved. Provider names and logos remain
identifiers of their respective projects, not an endorsement or trademark grant.

## Test dependency closure

`tests/offscreen/imports` contains 29 hash-pinned files. Seventeen host QML/JS
files match their `shell/Commons` or `shell/Ui` counterpart in Omarchy `v4.0.4`
byte-for-byte. `qs/Ui/Panel.qml` is a reduced lifecycle adapter and
`qs/Ui/KeyboardPanel.qml` replaces a native popup with an Item; they are
Omarchy-derived, retain applicable original text and use the root MIT license.
Three `qmldir` files restrict host registrations. The remaining eight files are
inert Quickshell adapters and registration files from the owner's integration
fixture, also published under MIT. Original local historical evidence is not
included or rewritten.

Adapters do not claim to be Quickshell runtime code: processes, file reads and
IPC are inert, detached execution and writes are rejected. Qt itself is an
external CI/test dependency, not vendored here. Tests do not certify a real shell
or the separately owned Pi collector.
