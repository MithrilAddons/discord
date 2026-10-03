# Discord foundation contract v1

`discord-foundation-v1.json` contains synthetic examples shared byte-for-byte with
the matching web change. Both repositories test the payloads. Compare fixture hashes
before publishing/deploying coordinated changes; a copied fixture is not automatic
cross-repository version synchronization. Pin the corresponding web revision in
release/deployment records. Incompatible changes require a new API version.

Every request uses `Authorization: Bearer <separate-internal-secret>` on the fixed
loopback listener at `127.0.0.1:8781`. Redirects and compressed/oversized responses
are rejected. No browser cookie, bot token or Minecraft credential authorizes it.

- `GET /internal/v1/summary`: aggregate counts for open, unpaused, uncompleted parties
  and searching players per floor; service check time; latest known version; recent
  Finder profile lookup state (`ok`, `slow`, `failing`, `unknown`). No names or UUIDs.
  Health is unknown after five minutes without an observed fetch, not fabricated OK.
- `GET /internal/v1/releases`: up to ten supported published releases, ordered by
  version descending, with exact official JAR URL, SHA-256 from GitHub asset metadata,
  bounded notes and official release/Modrinth page URLs. No drafts or assets lacking
  digests. Status is `ready`, `stale` or `unavailable`. The bot announces only ready
  data. Existing public download behavior remains separate and compatible.

These routes are read-only. Phase 1 adds no account links, event feed, voice mutations,
personal-data tables or alternate authentication path.
