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