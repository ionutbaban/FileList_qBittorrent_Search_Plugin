# FileList qBittorrent Search Plugin

Search FileList directly from qBittorrent using the official Python search plugin interface.

## Features

- qBittorrent-compatible single-file plugin
- FileList API integration with username + passkey credentials
- Name search
- IMDB search
- Combined IMDB + name filter, for example `tt0121955 s19e01`
- Category-aware searches from the qBittorrent category selector
- Optional API filters from the search box: `freeleech:1`, `internal:1`, `doubleup:1`, `moderated:1`, `season:19`, `episode:1`
- Latest torrents mode with `.` and optional `limit:N`
- Authenticated `.torrent` download flow for private tracker results

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
- If the API does not return a usable publish date, the plugin emits `-1` for `pub_date` as allowed by the qBittorrent plugin format.

## Testing

The official qBittorrent documentation recommends testing plugins through the Nova3 helper scripts rather than importing the plugin class directly.

### Official Nova3 smoke test

Bootstrap the helper files into a local ignored directory:

```bash
/home/ionut/projects/qbittorrent_filelist_search_plugin/.venv/bin/python scripts/bootstrap_nova3_harness.py
```

This downloads the Nova3 helper files from qBittorrent commit `89201bd142398c519ab998f70fbb5898723f4494` into `.qbt-test/nova3/`, creates `.qbt-test/nova3/engines/`, copies `filelist.py`, and copies `credentials.json` if it exists in the repository root. If `credentials.json` is missing, the bootstrap writes a placeholder from `credentials.json.example` so you can fill it in manually.

Run an official search smoke test:

```bash
/home/ionut/projects/qbittorrent_filelist_search_plugin/.venv/bin/python .qbt-test/nova3/nova2.py filelist all ubuntu
```

Run an IMDb + season smoke test:

```bash
/home/ionut/projects/qbittorrent_filelist_search_plugin/.venv/bin/python .qbt-test/nova3/nova2.py filelist tv tt0121955 s19e01
```

Run an official download smoke test with an actual `download_link` returned by the API:

```bash
/home/ionut/projects/qbittorrent_filelist_search_plugin/.venv/bin/python .qbt-test/nova3/nova2dl.py filelist "https://filelist.io/download.php?id=TORRENT_ID&passkey=YOUR_PASSKEY"
```

`nova2.py` should print only pipe-delimited search results to stdout. Any debug or error output belongs on stderr.

### Automated tests

Install the dev dependency and run pytest:

```bash
/home/ionut/projects/qbittorrent_filelist_search_plugin/.venv/bin/python -m pip install -r requirements-dev.txt
/home/ionut/projects/qbittorrent_filelist_search_plugin/.venv/bin/python -m pytest
```

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
*** Add File: /home/ionut/projects/qbittorrent_filelist_search_plugin/requirements-dev.txt
pytest>=8,<9
*** Add File: /home/ionut/projects/qbittorrent_filelist_search_plugin/pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
*** Add File: /home/ionut/projects/qbittorrent_filelist_search_plugin/scripts/bootstrap_nova3_harness.py
#!/usr/bin/env python3

import argparse
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path


QBT_REPO_REF = "89201bd142398c519ab998f70fbb5898723f4494"
QBT_NOVA3_BASE_URL = (
  "https://raw.githubusercontent.com/qbittorrent/"
  f"qBittorrent/{QBT_REPO_REF}/src/searchengine/nova3"
)
HELPER_FILES = (
  "nova2.py",
  "nova2dl.py",
  "helpers.py",
  "novaprinter.py",
  "socks.py",
)


def parse_args():
  parser = argparse.ArgumentParser(
    description="Bootstrap the official qBittorrent Nova3 helper files for local smoke testing."
  )
  parser.add_argument(
    "--target",
    default=".qbt-test/nova3",
    help="Directory where the Nova3 helper files will be created.",
  )
  parser.add_argument(
    "--plugin",
    default="filelist.py",
    help="Path to the plugin file that should be copied into the harness engines directory.",
  )
  parser.add_argument(
    "--credentials",
    default="credentials.json",
    help="Path to the credentials file to copy into the harness engines directory.",
  )
  parser.add_argument(
    "--force",
    action="store_true",
    help="Overwrite any existing helper files in the target directory.",
  )
  return parser.parse_args()


def download_helper_file(target_dir, filename, force):
  destination = target_dir / filename
  if destination.exists() and not force:
    return

  source_url = f"{QBT_NOVA3_BASE_URL}/{filename}"
  try:
    with urllib.request.urlopen(source_url, timeout=30) as response:
      destination.write_bytes(response.read())
  except urllib.error.URLError as error:
    raise SystemExit(f"Failed to download {source_url}: {error}")


def copy_plugin_files(project_root, target_dir, plugin_path, credentials_path):
  engines_dir = target_dir / "engines"
  engines_dir.mkdir(parents=True, exist_ok=True)
  (engines_dir / "__init__.py").write_text("", encoding="utf-8")

  source_plugin = (project_root / plugin_path).resolve()
  if not source_plugin.exists():
    raise SystemExit(f"Plugin file not found: {source_plugin}")

  shutil.copy2(source_plugin, engines_dir / source_plugin.name)

  source_credentials = (project_root / credentials_path).resolve()
  if source_credentials.exists():
    shutil.copy2(source_credentials, engines_dir / "credentials.json")
    return

  credentials_example = project_root / "credentials.json.example"
  if credentials_example.exists():
    shutil.copy2(credentials_example, engines_dir / "credentials.json")
    print(
      "credentials.json was not found at the project root; copied credentials.json.example instead.",
      file=sys.stderr,
    )
    return

  raise SystemExit("Neither credentials.json nor credentials.json.example could be found.")


def main():
  args = parse_args()
  project_root = Path(__file__).resolve().parents[1]
  target_dir = (project_root / args.target).resolve()
  target_dir.mkdir(parents=True, exist_ok=True)

  for helper_file in HELPER_FILES:
    download_helper_file(target_dir, helper_file, args.force)

  copy_plugin_files(project_root, target_dir, args.plugin, args.credentials)

  print(f"Nova3 smoke-test harness is ready at {target_dir}")


if __name__ == "__main__":
  main()
*** Add File: /home/ionut/projects/qbittorrent_filelist_search_plugin/tests/conftest.py
import sys
import types


stub_novaprinter = types.ModuleType("novaprinter")


def _unexpected_pretty_printer(_result):
  raise AssertionError("prettyPrinter should be monkeypatched by the test that uses it")


stub_novaprinter.prettyPrinter = _unexpected_pretty_printer
sys.modules.setdefault("novaprinter", stub_novaprinter)
*** Add File: /home/ionut/projects/qbittorrent_filelist_search_plugin/tests/test_filelist.py
import json
from pathlib import Path

import pytest

import filelist as filelist_module


@pytest.fixture
def configured_engine(monkeypatch):
  def fake_load(self):
    self._username = "user"
    self._passkey = "passkey"
    self._authorization_header = "Basic dXNlcjpwYXNza2V5"
    self._configuration_error = None

  monkeypatch.setattr(filelist_module.filelist, "_load_credentials", fake_load)
  return filelist_module.filelist()


@pytest.fixture
def printed_results(monkeypatch):
  results = []
  monkeypatch.setattr(filelist_module, "prettyPrinter", results.append)
  return results


def make_uninitialized_engine(credentials_path):
  engine = filelist_module.filelist.__new__(filelist_module.filelist)
  engine._credentials_path = credentials_path
  engine._username = ""
  engine._passkey = ""
  engine._authorization_header = ""
  engine._configuration_error = None
  return engine


def test_build_search_params_parses_documented_shorthand(configured_engine):
  params, latest_mode = configured_engine._build_search_params("tt0121955%20s19e01", "tv")

  assert latest_mode is False
  assert params["action"] == "search-torrents"
  assert params["type"] == "imdb"
  assert params["query"] == "tt0121955"
  assert params["season"] == "19"
  assert params["episode"] == "1"
  assert params["category"] == configured_engine.supported_categories["tv"]


def test_build_search_params_parses_latest_limit_and_category(configured_engine):
  params, latest_mode = configured_engine._build_search_params(".%20limit:999", "movies")

  assert latest_mode is True
  assert params == {
    "output": "json",
    "category": configured_engine.supported_categories["movies"],
    "action": "latest-torrents",
    "limit": "100",
  }


def test_request_json_retries_with_query_auth(configured_engine, monkeypatch):
  calls = []

  def fake_request_text(url, params, use_query_auth=False):
    calls.append(use_query_auth)
    if len(calls) == 1:
      raise filelist_module.FileListApiError("retry", retry_with_query_auth=True)
    return json.dumps([{"id": 1}])

  monkeypatch.setattr(configured_engine, "_request_text", fake_request_text)

  assert configured_engine._request_json({"action": "latest-torrents"}) == [{"id": 1}]
  assert calls == [False, True]


@pytest.mark.parametrize(
  ("value", "expected"),
  [
    ("2026-04-17 11:51:32", "1776426692"),
    ("2026-04-17T11:51:32", "1776426692"),
    ("2026-04-17T11:51:32+00:00", "1776426692"),
    (1776426692, "1776426692"),
    (1776426692000, "1776426692"),
  ],
)
def test_normalize_timestamp_supports_multiple_formats(configured_engine, value, expected):
  assert configured_engine._normalize_timestamp(value) == expected


def test_format_result_builds_desc_link_and_tags(configured_engine):
  formatted = configured_engine._format_result(
    {
      "id": 123,
      "name": "Example.Release",
      "download_link": "https://filelist.io/download.php?id=123&passkey=test",
      "upload_date": "2026-04-17 11:51:32",
      "size": 42,
      "seeders": 10,
      "leechers": 2,
      "freeleech": 1,
      "internal": 1,
      "doubleup": 0,
    },
    latest_mode=False,
  )

  assert formatted == {
    "desc_link": "https://filelist.io/details.php?id=123",
    "engine_url": "https://filelist.io",
    "leech": "2",
    "link": "https://filelist.io/download.php?id=123&passkey=test",
    "name": "[FREELEECH] [INTERNAL] Example.Release",
    "pub_date": "1776426692",
    "seeds": "10",
    "size": "42",
  }


def test_search_prints_unique_results(configured_engine, printed_results, monkeypatch):
  def fake_request_json(_params):
    return [
      {
        "id": 1,
        "name": "Result.One",
        "download_link": "https://filelist.io/download.php?id=1&passkey=test",
        "upload_date": "2026-04-17 11:51:32",
        "size": 1,
        "seeders": 2,
        "leechers": 3,
      },
      {
        "id": 2,
        "name": "Result.Duplicate",
        "download_link": "https://filelist.io/download.php?id=1&passkey=test",
        "upload_date": "2026-04-17 11:51:32",
        "size": 1,
        "seeders": 2,
        "leechers": 3,
      },
    ]

  monkeypatch.setattr(configured_engine, "_request_json", fake_request_json)

  configured_engine.search("ubuntu", "all")

  assert len(printed_results) == 1
  assert printed_results[0]["name"] == "Result.One"


def test_search_logs_api_errors_to_stderr(configured_engine, monkeypatch, capsys):
  def fake_request_json(_params):
    raise filelist_module.FileListApiError("boom")

  monkeypatch.setattr(configured_engine, "_request_json", fake_request_json)

  configured_engine.search("ubuntu", "all")

  captured = capsys.readouterr()
  assert captured.out == ""
  assert "Search failed: boom" in captured.err


def test_download_torrent_retries_and_writes_binary_file(configured_engine, monkeypatch, capsys):
  responses = [
    (b"<!DOCTYPE html><html></html>", "text/html; charset=utf-8"),
    (b"torrent-data", "application/x-bittorrent"),
  ]
  calls = []

  def fake_request_binary(url, use_query_auth=False):
    calls.append(use_query_auth)
    return responses.pop(0)

  monkeypatch.setattr(configured_engine, "_request_binary", fake_request_binary)

  configured_engine.download_torrent("https://filelist.io/download.php?id=1&passkey=test")

  captured = capsys.readouterr()
  output_parts = captured.out.strip().split(" ", 1)
  assert calls == [False, True]
  assert len(output_parts) == 2
  torrent_path = Path(output_parts[0])
  assert torrent_path.read_bytes() == b"torrent-data"
  torrent_path.unlink()


def test_download_torrent_logs_when_html_persists(configured_engine, monkeypatch, capsys):
  def fake_request_binary(_url, use_query_auth=False):
    return (b"<html></html>", "text/html")

  monkeypatch.setattr(configured_engine, "_request_binary", fake_request_binary)

  configured_engine.download_torrent("https://filelist.io/download.php?id=1&passkey=test")

  captured = capsys.readouterr()
  assert captured.out == ""
  assert "Download failed: FileList returned HTML instead of a torrent file." in captured.err


def test_load_credentials_reports_missing_file(tmp_path):
  engine = make_uninitialized_engine(tmp_path / "credentials.json")

  engine._load_credentials()

  assert "Missing credentials.json next to filelist.py" in engine._configuration_error


def test_load_credentials_reports_invalid_json(tmp_path):
  credentials_path = tmp_path / "credentials.json"
  credentials_path.write_text("not-json", encoding="utf-8")
  engine = make_uninitialized_engine(credentials_path)

  engine._load_credentials()

  assert "Invalid credentials.json" in engine._configuration_error
