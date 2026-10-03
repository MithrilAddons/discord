# Runtime configuration

The bot runs against an existing guild. Keep deployment-specific IDs and credential
paths in a private JSON file, outside the repository. This example uses placeholder IDs:

```json
{
  "guild_id": 100,
  "token_file": "bot-token.txt",
  "secret_file": "internal-secret.txt",
  "state_file": "bot.sqlite3",
  "staff_role": 200,
  "beta_role": 201,
  "linked_role": 202,
  "channels": {
    "welcome": 300,
    "how-to": 301,
    "releases": 302,
    "status": 303,
    "support": 304,
    "beta": 305,
    "audit-log": 306
  }
}
```

Use text channels for releases, status, beta, audit-log and how-to; support is a
forum. Welcome is used by the reusable information templates. Keep audit-log private
to staff and beta accessible to its intended role. Members should not be able to
post in releases/status. Staff bypasses message filtering; assign that role deliberately.

Runtime permissions are View Channels, Send Messages, Send Messages in Threads,
Embed Links, Read Message History and Manage Messages. The runtime does not need
Administrator or permission to create channels or manage roles. Keep Discord's
Message Content Intent enabled for attachment/link filtering. Discord AutoMod is
managed separately through server settings.

The internal secret is a separate random 32-byte lowercase hex value shared with
the backend listener. Never reuse the bot token as the internal secret. Relative
credential paths resolve under systemd's CREDENTIALS_DIRECTORY when present, or
the configuration directory locally. The state path resolves relative to the
configuration directory. See [Deployment](DEPLOYMENT.md) for production paths.

With `PYTHONPATH=src`, run:

```text
python -m mithril_discord run --config .local/config.json
```

Verify `/status` and `/release` replies are private. In a controlled test channel,
check a harmless empty `test.jar` attachment is removed, its author receives guidance,
and the audit contains no original message or attachment. Check edited links,
blocked DMs, support replies and that restarting does not duplicate status/release
posts. These live checks are separate from the offline tests.
