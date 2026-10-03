# Reusable server information

All server information is published as embeds. `messages.py` provides the shared
MithrilPF author, lavender accent (`#B4B8FF`) and footer through `info_embed`.
Use a clear card title, a short introduction and non-inline fields for sections.
Long guides can use multiple cards in one post. Keep links to official destinations.
Welcome and how-to cards are defined in `server_information`; the text below records
their content. Edit existing posts by their saved IDs instead of sending duplicates.
Status, releases, support guidance and safety notices use the same embed structure.
Persistent operational posts retain their footer identifiers for restart recovery.

## Welcome

MithrilPF helps you find Hypixel SkyBlock dungeon parties through the Minecraft mod
and website. Discord is optional. You can chat and ask for support without linking.

MithrilPF and its staff never ask for your Minecraft session ID, token or SSID.
Get the mod only from the official release links. Never install a JAR sent by a stranger.
Account verification and party voice are coming in later phases and are not enabled yet.

## Installation and checksums

Use the installation requirements published with the release at
https://github.com/MithrilAddons/mithrilpf/releases or https://modrinth.com/mod/mithrilpf.
Install the gameplay JAR, not the sources JAR. The website is https://mithril.foo.

On Windows, run `Get-FileHash -Algorithm SHA256 -LiteralPath 'path-to-downloaded.jar'`.
On Linux, run `sha256sum path-to-downloaded.jar`; on macOS, use
`shasum -a 256 path-to-downloaded.jar`. Compare all 64 hexadecimal characters with
the release post or official SHA256SUMS file. A mismatch means do not install it.
A checksum detects changed bytes; it does not independently authenticate a publisher.
The current release pipeline does not publish a detached JAR signature.

## Linking and troubleshooting

Use `/mpf` in Minecraft. Minecraft authentication happens through the mod and Mojang;
only Mojang receives the Minecraft access token. Browser linking requires confirming
the correct account on mithril.foo. Do not share screenshots of link codes or QR codes.
Discord linking is not part of the initial bot release.

For support, include mod, Minecraft and Fabric versions, what you expected, what
happened, and `/mithrilpfstatus` output. Remove account details and credentials from
logs. For invite problems, check all members are on Hypixel and whether another game
party conflicts. Automatic updates require an official release build and a restart.
