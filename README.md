# Omarchy Agents with Pi

A display-only Omarchy Agents clone with Pi-first ordering, a native Pi mark
and token-weighted cache statistics. Plugin ID: `slovn.agents`.

[Source](https://github.com/PavelLizunov/omarchy-agents-pi) ·
[CI](https://github.com/PavelLizunov/omarchy-agents-pi/actions/workflows/ci.yml) ·
[Stable update policy](docs/UPSTREAM.md) · [MIT license](LICENSE)

**Pi collection is not bundled.** This repository displays usage records that
an external collector has already produced. Installing the panel alone does
not collect Pi statistics or install the owner's local collector. Stock
collectors come from the Omarchy distribution. There is no standalone installer
or release package here; use this source only with the native Omarchy plugin
system and compatible usage records. No setup command is executed automatically.

The initial comparison base is stable Omarchy `v4.0.4`, commit
`c668141e9c42b13c80c9ca4ea108e11708c5e8a5`. All nine original Agents files match
that release byte-for-byte. This establishes a reproducible update base, not
historical fork ancestry. [Provenance](docs/PROVENANCE.md) explains the test adapters.

This user-owned clone (`slovn.agents`, cloned from `omarchy.agents`) keeps Pi first
without reordering other providers. Pi's native four-by-four mark is in
`assets/pi.svg`; its cells and brand colors follow Pi's native logo.

Pi's hero shows **All-time cache hit**; the seven local-calendar day rows show
both tokens and each day's cache-hit percentage. Percentages are calculated by
summing `cacheRead`, `input`, and `cacheWrite` tokens over the selected period,
then dividing `cacheRead / (input + cacheRead + cacheWrite)`. Output is excluded;
this is not an arithmetic mean of request or day percentages. The owner's external collector
includes assistant, toolResult, standalone usage, compaction and branch_summary
usage, matching the Pi footer extension's `Σ` entry scope; that collector is not
part of this repository and its correctness is not certified by this CI. Missing counters or
no input produce `—`, while a known no-hit day shows `0.0%`. Unattributed usage
stays in an explicit Unattributed model bucket rather than guessing a model.
The panel covers all saved sessions; footer `Σ` covers one session, so values
need not match. Nothing changes Pi's model-facing context or requests.

The panel invokes `omarchy-agent-usage-update` through the Omarchy command path.
Refresh is configurable: the manifest defaults to 900 seconds; the owner's
installation uses 300 seconds. Other providers retain stock UI and collection
behavior. Cross-device cache percentages are not implemented: stock
sync discards the extra daily cache counters, so merged Pi days show `—` and the
hero remains the local history ratio. Sync defaults to Off.

The clone survives package updates. A weekly/manual GitHub workflow checks
stable upstream releases and prepares tested update PRs; it never automatically
merges or deploys them. When reconciling an updated stock plugin, preserve
Pi-first ordering, native Pi icon selection, per-day cache labels and their
tooltips, non-Pi presentation, and the clone metadata. To switch back without deleting
the clone, use `omarchy plugin enable omarchy.agents`; this restores the source
widget through the native clone mechanism.

Run the self-contained inert checks with `python3 -B tests/run.py`; see
[verification instructions and limits](tests/README.md). The separately selected
`--known-bug` option runs the icon-switch regression, also covered by the default
suite. The local correction rejects stale fallback callbacks; live host and
qml-preview acceptance remain unverified.
The upstream guide below refers to collectors in the Omarchy distribution,
not bundled collector scripts in this checkout. Its `omarchy.agents` commands
are stock examples; use `slovn.agents` to target this clone. Enabling the stock
plugin instead switches away from the clone. The clone currently inherits the
stock IPC target; simultaneous instances/IPC isolation are not certified.

CI verifies static contracts and an inert offscreen consumer with Qt 6.8.3;
local verification used Qt 6.11.2. It does not certify the external collector,
future shell APIs, live compositor input or qml-preview MCP acceptance. No
independent review or complete repository hygiene signoff is claimed.

One bar icon and one panel for every AI coding subscription on the machine.
The panel is strictly a display: it watches the usage records that
`omarchy-agent-usage-update` writes to `~/.local/state/omarchy/agents/usage/`
and draws whatever appears there. `Panel.qml` owns the bar button and the
popup; `Main.qml` discovers and watches the records (and handles the optional
cross-device aggregation); `Agent.qml` is the per-record file watcher.

## Panel

- **Hero** — the mark, the tool, and the plan it runs on ("Max 20x", "Pro").
  Auth and endpoint problems replace the plan line and repeat in a card.
- **Subscription switch** — one chip per enabled agent (`h`/`l` or click).
  It appears only when more than one agent is enabled.
- **Limits** — the percentage of each allowance used, a matching meter, and
  the time until the session or weekly window resets.
- **Balance** — prepaid agents report a credit ledger instead of limits:
  remaining credit, a fuel-gauge meter that drains toward empty, and
  funded-versus-spent detail.
- **Tokens by day** — one row per day for the last week: day, bar, tokens, with today
  bolded at the bottom. Hover today for its prompt and session count.
- **Tokens by model** — tokens per model with the bar behind each row scaled
  to the heaviest model,
  the same way the weekly chart scales to its busiest day. Hover for the
  input / output / cache split.

A subscription appears only when it is enabled in settings and has actually
recorded usage — on this machine or on a synced one. With one such agent
there is no switch row at all; with none, the module leaves the bar entirely
rather than sitting there with nothing to say. A CLI installed mid-session
shows up at the next refresh, so nothing polls the disk waiting for it.

That self-hiding is why the widget ships in the default bar layout: a machine
that has never run an AI coding agent draws nothing, and the icon arrives on
its own the first time a scan finds usage. Drop it with
`omarchy plugin disable omarchy.agents`.

## Data

Each agent is one JSON record in `~/.local/state/omarchy/agents/usage/`,
written by `omarchy-agent-usage-update`. That command runs one
`omarchy-agent-usage-<agent>` collector per agent; the widget invokes it
on its refresh timer and whenever you ask for a refresh, and picks up any
record that lands in the directory regardless of who wrote it.

Adding an agent therefore never touches this plugin: ship a collector that
prints the record contract (see the `claude` and `codex` collectors in
`bin/`), and the panel gains a tab. An `assets/<id>.svg` mark is optional —
with an `assets/<id>-light.svg` twin if the mark needs a dark variant for
light surfaces — and the bar glyph stands in when there is none.

| Collector | Limits | Local stats |
|---|---|---|
| `claude` | Anthropic's OAuth usage endpoint (5-hour session + 7-day weekly) | `~/.claude/projects` transcripts, opencode sessions on an Anthropic provider, plus `stats-cache.json` and `history.jsonl` as fallback |
| `codex` | The Codex app-server RPC | native Codex CLI session files (plus pi and opencode sessions) |
| `fireworks` | Estimated prepaid balance: configured funding minus rated account costs | Fireworks billing API, grouped by day and model for the last 30 days |

Claude limits need a signed-in CLI; without credentials the panel says so and
falls back to local stats only. A non-default Claude directory is honored via
`CLAUDE_CONFIG_DIR`, Codex via `CODEX_HOME`. Fireworks reads
`FIREWORKS_API_KEY` and `FIREWORKS_ACCOUNT_ID` first, then
`~/.fireworks/auth.ini` (which `firectl set-api-key` creates), then the key
opencode stores in `~/.local/share/opencode/auth.json` when Fireworks is
signed in there.

### Fireworks balance

The collector first asks the account's `:getBalance` endpoint for the real
prepaid ledger. That endpoint exists but is permission-gated, and as of
August 2026 no console-issued API key passes it — Fireworks appears to
reserve it for the dashboard session. The probe stays because it is cheap
and the live figure lights up automatically if Fireworks ever opens it to
keys. Until then the collector falls back to estimating the balance from
configuration in `~/.config/omarchy/agents/fireworks.json`:

```json
{
  "accountId": "",
  "fundedAmount": 20,
  "fundedAt": "2026-07-01"
}
```

Set `fundedAmount` to the credits purchased and optionally `fundedAt` to the
purchase date; with no date, the collector uses the account creation time. It
subtracts rated account costs and the panel labels the result as estimated.
For a later top-up, increase `fundedAmount` by the new credit while keeping
the original `fundedAt`, so both the funding and spend still cover the same
period. `accountId` only matters when one API key can access several
accounts. Without a configured `fundedAmount` the tab still shows token
usage, just no balance. With a live ledger, `fundedAmount` is optional and
only adds the meter and the spent-of-funded line under the real figure.

## Interactions

- Bar icon: left = panel, right = launch agent, middle = next subscription.
- Panel: `h`/`l` switch subscription, `j`/`k` scroll, `r` or Enter refresh,
  Tab moves to the neighboring bar panel, Esc closes.
- IPC: `omarchy-shell omarchy.agents <open|close|toggle|refresh|next>`.

## Settings

Settings live in the widget's entry in `~/.config/omarchy/shell.json`. The
top-level keys can be set with
`omarchy bar set omarchy.agents <key> <value>`:

| Key | Default | What it does |
|---|---|---|
| `refreshIntervalSec` | `900` | How often the usage records regenerate |
| `syncMode` | `"Off"` | `"On"` writes this machine's snapshot and merges the others |
| `syncDir` | `""` | A folder synced by Syncthing, Dropbox, rsync, … |
| `syncFileName` | `<hostname>.json` | This machine's snapshot file |
| `syncDeviceId` | hostname | Stable device name inside the snapshot |

Numbers need `--json`, or they land in `shell.json` as strings:

```bash
omarchy bar set omarchy.agents refreshIntervalSec 300 --json
omarchy bar set omarchy.agents syncDir '~/Sync/agent-usage'
```

Per-agent enablement is nested, and `set` writes its key literally rather
than walking a dotted path — so pass the whole `providers` object as JSON (or
edit `shell.json` directly):

```bash
omarchy bar set omarchy.agents providers '{
  "claude": { "enabled": true },
  "codex": { "enabled": false },
  "fireworks": { "enabled": true }
}' --json
```

`enabled` defaults to `true` for every discovered agent; set it to `false` to
hide a subscription that is installed. Disabled agents are also skipped when
the records regenerate.

With `syncMode` on, every `*.json` snapshot in `syncDir` is merged, so today,
the last 7 days, and the all-time totals cover every machine you code on —
active days are unioned by date rather than summed. Rate limits stay
per-account and are never merged. A record may declare `"scope": "account"`
when its stats are account-global rather than machine-local (Fireworks'
billing API); those merge by taking the widest value instead of summing, so
the same account synced from two machines is not counted twice.

One caveat on "all-time": the Codex collector only reads native session files
touched in the last 30 days, and Fireworks requests the last 30 days from its
billing API, so their totals and day counts cover that window. Claude's cover
every transcript still on disk.
