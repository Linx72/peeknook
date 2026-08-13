# PeekNook public releases

This repository is the public delivery channel for signed PeekNook Desktop
artifacts. It is not the PeekNook source repository and must never contain source
code, build credentials, signing keys, user data, or CI secrets.

Each updater release must contain:

- `latest.json` with Tauri updater metadata;
- a signed macOS updater archive and its `.sig` file;
- a signed Windows updater installer and its `.sig` file;
- user-installable macOS and Windows packages when available.

Artifacts must be built, signed, notarized where applicable, and verified in the
private source pipeline before publication. The public repository is a delivery
channel only; it does not make an unverified build trustworthy.

The channel contract is recorded in `channel.json`. Anonymous repository access
is enabled, but an installed client must not be pointed at this repository until
a real signed release asset and a signed bridge release have both been verified.

Before publication, the source pipeline validates the complete staged bundle
with `scripts/peeknook-publish-repobase-release.py`. The command is validate-only
by default. Mutation additionally requires `--publish`, the exact repository
confirmation, and a scoped token read from the environment. The remote release
stays a draft until every expected asset has been uploaded and inventoried. A
retry accepts an existing published release only after downloading and matching
the name, size, and SHA-256 of every asset; it never overwrites a remote file.
