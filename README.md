# MithrilPF Discord

Optional community infrastructure for [MithrilPF](https://github.com/MithrilAddons/mithrilpf).
Original code is MIT licensed; see [LICENSE](LICENSE).

This repository owns the Discord bot, reusable message templates, tests and deployment files.
[MithrilAddons/web](https://github.com/MithrilAddons/web) owns identity, parties,
moderation, erasure and the authenticated internal API. Minecraft integration and
desktop Rich Presence remain in the mod. Discord is never required to use the finder.

The first implementation includes executable/upload and suspicious-download filtering,
support forum guidance, `/status`, `/release`,
release announcements and a persistent status post. It requires the matching backend
extension before release/status features can run. It has not yet been deployed.

Verification, stat roles, DM subscriptions, party voice and moderation-case forwarding
are later phases. Party voice must remain available throughout dungeon runs;
Minecraft handoff completion must never trigger its deletion.

- [Development and checks](docs/DEVELOPMENT.md)
- [Architecture and rollout](docs/ARCHITECTURE.md)
- [Runtime configuration and permissions](docs/CONFIGURATION.md)
- [Reusable information embeds](docs/SERVER_CONTENT.md)
- [Deployment and recovery](docs/DEPLOYMENT.md)
- [Internal contract](contracts/README.md)
