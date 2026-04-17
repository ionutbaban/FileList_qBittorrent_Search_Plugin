import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.live

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
BOOTSTRAP_SCRIPT = "scripts/bootstrap_nova3_harness.py"
NOVA2_SCRIPT = ".qbt-test/nova3/nova2.py"
NOVA2DL_SCRIPT = ".qbt-test/nova3/nova2dl.py"
CREDENTIALS_PATH = REPO_ROOT / "credentials.json"


def _run_command(*args):
    return subprocess.run(
        [PYTHON, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _format_process_result(result):
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    parts = ["returncode=%s" % result.returncode]
    if stdout:
        parts.append("stdout=%s" % stdout)
    if stderr:
        parts.append("stderr=%s" % stderr)
    return " | ".join(parts)


def _output_lines(result):
    return [line for line in result.stdout.splitlines() if line.strip()]


def _assert_pipe_delimited(lines):
    assert all(line.count("|") == 7 for line in lines), lines


@pytest.fixture(scope="session")
def live_repo_root():
    if not CREDENTIALS_PATH.exists():
        pytest.skip("Live Nova3 tests require credentials.json in the repository root.")
    return REPO_ROOT


@pytest.fixture(scope="session")
def nova3_harness(live_repo_root):
    result = _run_command(BOOTSTRAP_SCRIPT)
    assert result.returncode == 0, _format_process_result(result)
    assert (REPO_ROOT / NOVA2_SCRIPT).exists()
    assert (REPO_ROOT / NOVA2DL_SCRIPT).exists()
    return live_repo_root


@pytest.mark.parametrize(
    ("category", "query_parts"),
    [
        ("all", ("ubuntu",)),
        ("tv", ("simpsons",)),
        ("movies", (".",)),
    ],
)
def test_nova3_search_smoke_returns_results(nova3_harness, category, query_parts):
    result = _run_command(NOVA2_SCRIPT, "filelist", category, *query_parts)

    assert result.returncode == 0, _format_process_result(result)
    assert result.stderr.strip() == "", _format_process_result(result)

    lines = _output_lines(result)
    assert lines, _format_process_result(result)
    _assert_pipe_delimited(lines)


def test_nova3_episode_filter_query_exits_cleanly(nova3_harness):
    result = _run_command(NOVA2_SCRIPT, "filelist", "tv", "tt0121955", "s19e01")

    assert result.returncode == 0, _format_process_result(result)
    assert result.stderr.strip() == "", _format_process_result(result)
    _assert_pipe_delimited(_output_lines(result))


def test_nova3_download_smoke_returns_torrent_payload(nova3_harness):
    search = _run_command(NOVA2_SCRIPT, "filelist", "all", "ubuntu")
    assert search.returncode == 0, _format_process_result(search)
    assert search.stderr.strip() == "", _format_process_result(search)

    lines = _output_lines(search)
    assert lines, _format_process_result(search)
    link = lines[0].split("|", 1)[0]

    download = _run_command(NOVA2DL_SCRIPT, "filelist", link)
    assert download.returncode == 0, _format_process_result(download)
    assert download.stderr.strip() == "", _format_process_result(download)

    output = download.stdout.strip()
    assert output, _format_process_result(download)

    torrent_path = Path(output.split(" ", 1)[0])
    try:
        assert torrent_path.exists(), _format_process_result(download)
        data = torrent_path.read_bytes()
        lowered = data[:256].lower().lstrip()
        assert not lowered.startswith(b"<!doctype"), "Expected torrent payload, got HTML doctype."
        assert not lowered.startswith(b"<html"), "Expected torrent payload, got HTML page."
    finally:
        torrent_path.unlink(missing_ok=True)