# FileList qBittorrent Search Plugin

Search FileList directly from qBittorrent using the official Python search plugin interface.

## Features

- qBittorrent-compatible single-file plugin
- FileList API integration with username + passkey credentials
- Name search
- IMDb search
- Combined IMDb + name filter, for example `tt0121955 s19e01`
- Category-aware searches from the qBittorrent category selector
- Optional API filters from the search box: `freeleech:1`, `internal:1`, `doubleup:1`, `moderated:1`, `season:19`, `episode:1`
- Latest torrents mode with `.` and optional `limit:N`
- Authenticated `.torrent` download flow for private tracker results
- Official Nova3 smoke-test harness and pytest regression suite

## Requirements

- qBittorrent with Python search plugins enabled
- A FileList account
- Your FileList username
- Your FileList passkey

The passkey is not your login password. It is shown on your FileList profile page at `https://filelist.io/my.php`, near `Reset passkey`, as a long hexadecimal string.

## Files

- `filelist.py` - the plugin file you install in qBittorrent
- `credentials.json.example` - template for your credentials file
- `credentials.json` - your real credentials file, kept out of git
- `scripts/bootstrap_nova3_harness.py` - downloads the official Nova3 helper files for local smoke testing
- `tests/` - automated pytest coverage for parser, API, and download behavior

## Install

1. Copy `filelist.py` to your qBittorrent search engines directory.
2. Copy `credentials.json.example` to `credentials.json` in the same directory.
3. Edit `credentials.json` and fill in your FileList username and passkey.
4. In qBittorrent, open `Search plugins...`, choose `Install a new one`, then select `filelist.py`.

Typical engines directories:

- Linux: `~/.local/share/qBittorrent/nova3/engines/`
- Windows: `%localappdata%\qBittorrent\nova3\engines\`
- macOS: `~/Library/Application Support/qBittorrent/nova3/engines/`

## credentials.json

```json
{
  "username": "YOUR_USERNAME",
  "passkey": "YOUR_PASSKEY"
}
```

## Search Syntax

The qBittorrent search UI only provides one text box, so the plugin supports a small query syntax to expose the FileList API features.

### Standard searches

- `ubuntu`
- `the last of us`
- `tt0121955`
- `tt0121955 s19`
- `tt0121955 s19e01`

### Optional filters

Use these as extra tokens in the query:

- `freeleech:1` or `freeleech:0`
- `internal:1` or `internal:0`
- `doubleup:1` or `doubleup:0`
- `moderated:1` or `moderated:0`
- `season:19`
- `episode:1`

Examples:

- `ubuntu freeleech:1`
- `tt0121955 internal:1`
- `tt0121955 season:19 episode:1`
- `tt0121955 s19`
- `tt0121955 s19e01 freeleech:1`

### Latest torrents mode

Use `.` as the full query to call the FileList `latest-torrents` endpoint.

Examples:

- `.`
- `. limit:20`
- `. tt0121955`

In latest mode, extra free-text terms are ignored because the FileList API does not support name filtering on `latest-torrents`.

## Category Mapping

The plugin supports these qBittorrent categories:

- `all`
- `movies`
- `tv`
- `music`
- `games`
- `anime`
- `software`

`books` and `pictures` are not exposed because FileList does not provide matching categories.

## Notes

- FileList returns `.torrent` download links, not magnet links.
- The plugin implements authenticated torrent download to improve compatibility with private tracker downloads.
- qBittorrent categories such as `movies` and `tv` expand into their underlying FileList category ids for `search-torrents`, so one qBittorrent search can cover all mapped subcategories.
- If the API does not return a usable publish date, the plugin emits `-1` for `pub_date` as allowed by the qBittorrent plugin format.

## Testing

The official qBittorrent documentation recommends testing plugins through the Nova3 helper scripts rather than importing the plugin class directly.

### Offline tests

With the repository virtual environment activated, install the dev dependency and run the local regression suite:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

This covers the parser, formatting, auth fallback, and download behavior without requiring live FileList access.

### Remote live tests

Live FileList validation should be run on the reachable host because `filelist.io` is blocked on the current local host. The remote checkout is at `~/projects/FileList_qBittorrent_Search_Plugin`.

After connecting to the reachable host, run these commands from `~/projects/FileList_qBittorrent_Search_Plugin`.

These commands assume the repository virtual environment is activated on the reachable host.

Run the remote regression suite:

```bash
python -m pytest
```

Run the integrated live Nova3 pytest suite:

```bash
python -m pytest --live -m live
```

This opt-in suite bootstraps the Nova3 harness, runs the live search smoke tests, and verifies that the download smoke test returns a torrent payload.

### Manual Nova3 debugging

Use these commands only when you need to debug a specific live failure outside the integrated live pytest suite.

Bootstrap the helper files:

```bash
python scripts/bootstrap_nova3_harness.py
```

Re-run the bootstrap script after changing `filelist.py` or `credentials.json` so the harness copy stays current.

Run the manual search smoke tests:

```bash
python .qbt-test/nova3/nova2.py filelist all ubuntu
python .qbt-test/nova3/nova2.py filelist tv simpsons
python .qbt-test/nova3/nova2.py filelist tv tt0121955 s19e01
python .qbt-test/nova3/nova2.py filelist movies .
```

`tv simpsons` is the positive-result TV smoke test. `tv tt0121955 s19e01` is still useful as an episode-filter query, but it may legitimately return zero rows depending on current tracker contents.

Run the manual download smoke test with an actual `download_link` returned by the API:

```bash
link=$(python .qbt-test/nova3/nova2.py filelist all ubuntu | awk -F'|' 'NR==1 {print $1; exit}')
python .qbt-test/nova3/nova2dl.py filelist "$link"
```

`nova2.py` should print only pipe-delimited search results to stdout. Any debug or error output belongs on stderr.

The preferred live validation path is still `python -m pytest --live -m live`.

## Troubleshooting

### `Invalid passkey/username!`

- Verify that you are using your FileList username, not email.
- Verify that the passkey is the long hex string shown on `https://filelist.io/my.php`, near `Reset passkey`.
- Remove accidental leading or trailing whitespace from both values.
- If you recently reset the passkey, update `credentials.json`.
- If authentication still fails, monitor or reply on the FileList forum thread about the API at `https://filelist.io/forums.php?action=viewtopic&topicid=120435&page=last#7289887`.

### No results in qBittorrent

- Check qBittorrent's search plugin console or stderr logs for `[filelist]` messages.
- Confirm that `credentials.json` is next to `filelist.py` in the engines directory.
- Try a simple query such as `ubuntu` or `tt0121955`.

### WebUI note

qBittorrent's WebUI still relies on the backend search plugin system. If a result downloads incorrectly, verify that the backend can access FileList and that the credentials are valid.

### Download smoke test returns HTML

- Use the exact `download_link` returned by the API, not a manually constructed placeholder id.
- Confirm that the FileList account can actually download torrents. Account state problems can return an HTML error page instead of a `.torrent` file.
- If the first request returns HTML, the plugin retries the download with explicit query authentication.

### Shell smoke tests show BrokenPipeError

- Re-run `python scripts/bootstrap_nova3_harness.py` after updating the plugin so the harness copy includes the current broken-pipe handling.
- The current plugin stops cleanly when stdout closes early during shell pipelines.
