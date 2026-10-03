# Architecture and rollout

The bot is a separate Python/discord.py process on the backend host. It only calls
fixed `127.0.0.1:8781/internal/v1` endpoints, with a separate shared secret. It
never imports backend code, reads backend databases or holds the Hypixel key.
GitHub release polling is performed by the backend's existing ReleaseCache.

Phase 1 implements community-message safety,
support forum guidance, release posts and status. The original design's claim
that this phase requires no backend work does not hold for the existing API:
the version/JAR link response lacks checksums, notes, counts and lookup health.
A minimal read-only internal backend extension supplies those fields. The public
release response remains unchanged. No detached JAR signature exists in the
current release pipeline; posts explicitly say so. SHA-256 is integrity metadata,
not an independent publisher signature.

Commands are registered only in the configured guild. Phase 1 replies are ephemeral.
Status is edited every 60 seconds. Three consecutive failed backend checks create
one persistent incident post, subsequently edited through failure and recovery.
Release metadata is polled every five minutes. The latest ten supported releases
are considered; each is posted once per destination, with prereleases also in beta.
Only the configured Beta tester role can be mentioned by a release post. Plain
code-block notes cannot create disguised Markdown download buttons.

SQLite stores only operational message IDs keyed by purpose/version. After a crash
between sending and saving, the bot searches the latest 100 channel messages for
its marker before retrying. This bounds recovery work; it is not an exactly-once
delivery guarantee if a marker has already fallen outside that window. Preserve
the state database. Ordinary Discord messages are not cached by the client or
saved in local storage. Discord itself retains posts and staff audit messages.
Audit entries contain author/message IDs, a rule and filename hashes, never file
contents or the original message. Logging suppresses event/HTTP payloads.

The filter runs on new and edited messages from non-staff. It checks executable
extensions, new-member restrictions and exact official hosts/paths. In a message
mentioning mods/downloads/MithrilPF, any nonofficial HTTP(S) link is removed; this
conservative policy can require staff to review legitimate external links. Shorteners
and lookalike domains outside that context are flagged. It is not a malware scanner
or a guarantee against malicious files, obfuscated text, compromised publishers or
future Discord message types. AutoMod supplies a separate spam/slur layer.

Later phases, in order:

1. Backend-owned verification, unique links, unlink/erasure, stat refresh and roles.
   Revisit stale/reassigned Discord username risks before treating the Hypixel field
   as sufficient proof. Keep Mojang lookup on the backend to match the process boundary.
2. Opt-in notifications and private party voice. Keep voice through game handoff and
   during the run; delete on actual party closure or ten minutes empty. Membership,
   linking changes, reconnects and backend restart must reconcile access. Use an event
   epoch as well as sequence so restarting an in-memory feed cannot strand a saved cursor.
3. Audited backend report summaries to the staff queue and release/bug-post tagging.

Backend-only personal data and atomic erasure must be established before adding
identity links. The later event feed, voice state, schemas and moderation mutations
are deliberately not stubbed into the Phase 1 contract.
