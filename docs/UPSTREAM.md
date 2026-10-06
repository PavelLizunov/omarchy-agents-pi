# Stable upstream updates

## Reproducible base

`.upstream/base.json` pins the Omarchy repository, numbered stable tag, commit
and SHA-256 of every Agents file. `.upstream/agents/` holds that exact upstream
subtree. It is comparison data, not deployed plugin code or historical ancestry.

## Automation

CI runs on pushes, pull requests and manual dispatch. The stable-update workflow
runs Mondays at 07:23 UTC and on manual dispatch. It queries only
`omacom/omarchy`'s latest published non-prerelease GitHub release; `quattro`,
draft releases and prereleases are excluded.

The updater resolves the release tag to a commit, rejects unsupported paths,
entry points, symlinks and excessive content, and uses a temporary Git repository
for a three-way merge: previous upstream snapshot, current plugin, new upstream.
This preserves local changes where Git can reconcile them. Conflicts stop the
workflow before checkout mutation. New unsupported subtree files require manual
review instead of being silently ignored.

A read-only-token job checks the merged candidate. Only a successful candidate
patch reaches a separate publishing job. That job accepts only the five plugin
root files, flat SVG assets and matching upstream metadata/snapshot. It checks
that main has not moved, creates `upstream/vX.Y.Z`, and opens a PR. It never
force-pushes or replaces an existing update branch. One upstream PR may be open
at a time; merge or close it before requesting another update.

GitHub normally suppresses workflow events produced by `GITHUB_TOKEN`. The
publishing job therefore explicitly dispatches CI on the update branch.
Reviewers must verify a green run for the PR's exact head commit, inspect the
diff and test the compatible native host before merging. Automation never
merges a PR or changes the installed desktop.

If branch push succeeds but PR creation/CI dispatch fails, the workflow is red.
Recover by reviewing the existing branch, opening its PR and manually running
CI on that branch; do not delete or force-push it merely to make automation pass.

## GitHub permissions and dependencies

The repository must allow Actions to create pull requests. The preparation job
has only `contents: read`. The publication job has `contents: write`,
`pull-requests: write` and `actions: write` for branch push, PR creation and
explicit CI dispatch. No personal access token or collector credential is used.
CI does not use `pull_request_target` and does not expose a write token to PR code.
Actions that checkout or transfer artifacts are pinned to commit hashes.

Only GitHub-hosted Ubuntu runners install CI dependencies: Qt 6.8.3 using pinned
`aqtinstall==3.3.0` and `py7zr==1.1.0`, plus system libraries/fonts. Downloads and
font/package availability remain external dependencies. Nothing installs on
maintainers' machines. There is no broad Qt matrix or model API test budget.

## Checks and limitations

- Static snapshot, clone identity, inherited README suffix and upstream-identical
  file contracts.
- Python AST, JSON and SVG parsing, credential-pattern scan and whitespace.
- Offline merge preservation, disjoint updates, conflicts, additions/deletions,
  path and size rejection.
- Fixture lock/output guards, QML parsing and isolated actual-consumer scenarios.
- Logs, source hashes and PNG evidence retained as Actions artifacts.

These are bounded checks, not a proof of arbitrary future compatibility. The
fixtures pin host controls; an update that changes host API dependencies may
need a separate reviewed fixture refresh. Collector behavior, live Hyprland
routing, focus, IPC isolation and qml-preview acceptance are not tested here.
No auto-release, auto-deployment or independent-model review is configured.
