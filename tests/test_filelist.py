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


def test_search_fans_out_multi_category_requests(configured_engine, printed_results, monkeypatch):
    requested_categories = []

    def fake_request_json(params):
        requested_categories.append(params["category"])
        return [
            {
                "id": params["category"],
                "name": "Result.%s" % params["category"],
                "download_link": "https://filelist.io/download.php?id=%s&passkey=test" % params["category"],
                "upload_date": "2026-04-17 11:51:32",
                "size": 1,
                "seeders": 2,
                "leechers": 3,
            }
        ]

    monkeypatch.setattr(configured_engine, "_request_json", fake_request_json)

    configured_engine.search("tt0121955 s19e01", "tv")

    assert requested_categories == ["13", "21", "23", "27"]
    assert len(printed_results) == 4


def test_search_stops_cleanly_on_broken_pipe(configured_engine, monkeypatch, capsys):
    printer_calls = []

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
                "name": "Result.Two",
                "download_link": "https://filelist.io/download.php?id=2&passkey=test",
                "upload_date": "2026-04-17 11:51:32",
                "size": 1,
                "seeders": 2,
                "leechers": 3,
            },
        ]

    def fake_pretty_printer(_result):
        printer_calls.append(1)
        raise BrokenPipeError()

    monkeypatch.setattr(configured_engine, "_request_json", fake_request_json)
    monkeypatch.setattr(filelist_module, "prettyPrinter", fake_pretty_printer)

    configured_engine.search("ubuntu", "all")

    captured = capsys.readouterr()
    assert len(printer_calls) == 1
    assert captured.out == ""
    assert captured.err == ""


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