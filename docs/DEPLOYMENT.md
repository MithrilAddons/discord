# Deployment and recovery

Deploy the tested backend extension first, then the independently tested bot.

For leaderboards, deploy the matching backend first and configure the private
`channels.leaderboards` ID. Keep channel creation as an operator setup action,
outside published runtime code. Verify the three cards, a new mod PB, terminal
ties, moderation/erasure, unavailable/recovery behavior and restart without
duplicates. Offline tests do not establish actual Minecraft capture or Discord rendering.
Backend publication must satisfy the web repository's source-availability workflow.
Do not place the bot inside the web process, reuse its service account, or expose
port 8781 through nginx. No CI workflow deploys.

Use an unprivileged `mithril-discord` system user and:

- `/opt/mithril-discord/releases/<revision>/`: source plus a locked production venv.
- `/opt/mithril-discord/current`: atomic active-release symlink.
- `/etc/mithril-discord/`: private configuration, token and internal secret.
- `/var/lib/mithril-discord/bot.sqlite3`: service-owned operational state, outside releases.

Export dependencies with `uv export --locked --no-dev --no-emit-project`; install
them into the release venv with hashes enforced. Copy src, deploy, LICENSE and
the lockfile/build instructions. Exclude `.local`, tests' generated output, tokens
and databases. Keep the prior release and verify source/dependency hashes.

Keep `bot-token.txt` and `internal-secret.txt` root-owned mode 0600. The service uses
systemd LoadCredential to expose each secret privately to its unprivileged process.
The backend's optional `deploy/discord-listener.conf` drop-in loads the same internal
secret; it never receives the bot token. No shared database access is granted.

Create `/etc/mithril-discord/config.json` using the schema in [Configuration](CONFIGURATION.md)
with the existing guild's role/channel IDs. Set `token_file` to `bot-token.txt`,
`secret_file` to `internal-secret.txt`,
and `state_file` to `/var/lib/mithril-discord/bot.sqlite3`. Credential-relative paths
use systemd's CREDENTIALS_DIRECTORY; local development uses the config directory.
Make the nonsecret config readable only by root/the service group.

Install `deploy/mithril-discord.service`, validate the unit, switch the release
symlink atomically and start just this service. Verify both listeners are loopback,
unauthenticated internal reads fail, public `/internal/v1/*` remains 404, Discord
permissions are correct, and restart preserves post IDs. Observe actual release/status
posts and filter behavior before considering the deployment verified.

Rollback the bot by restoring its previous source symlink, preserving its database.
The backend tolerates no bot. A bot rollback never requires a backend/database rollback.
Back up operational SQLite using its backup API with the bot stopped, retain privately,
and remove unnecessary stale backups. Revoke a leaked bot token through Discord;
replace the root-only credential file and restart. Rotate the internal secret by
replacing its root-only file and restarting both services. Never print credentials.
