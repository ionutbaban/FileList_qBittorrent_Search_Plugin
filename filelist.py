# VERSION: 1.0
# AUTHORS: GitHub Copilot

import base64
import datetime
import json
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from novaprinter import prettyPrinter


API_URL = "https://filelist.io/api.php"
USER_AGENT = "qBittorrent-FileList-Plugin/1.0"
IMDB_RE = re.compile(r"^(?:tt)?(\d{7,8})$", re.IGNORECASE)
SEASON_EPISODE_RE = re.compile(r"^s(?P<season>\d+)(?:e(?P<episode>\d+))?$", re.IGNORECASE)
FLAG_FILTERS = frozenset(("doubleup", "freeleech", "internal", "moderated"))
DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%d-%m-%Y %H:%M:%S",
)
HTTP_STATUS_MESSAGES = {
    400: "Invalid search or filter.",
    401: "Username and passkey cannot be empty.",
    403: "Authentication failed or too many failed authentications.",
    429: "Rate limit reached.",
    503: "Service unavailable.",
}
ALL_CATEGORY_IDS = ",".join(str(value) for value in range(1, 28))


class FileListApiError(Exception):
    def __init__(self, message, status_code=None, retry_with_query_auth=False):
        super().__init__(message)
        self.status_code = status_code
        self.retry_with_query_auth = retry_with_query_auth


class filelist(object):
    url = "https://filelist.io"
    name = "FileList"
    supported_categories = {
        "all": ALL_CATEGORY_IDS,
        "anime": "15,24",
        "games": "9,10",
        "movies": "1,2,3,4,6,16,19,20,25,26",
        "music": "5,11,12",
        "software": "8,17,22",
        "tv": "13,21,23,27",
    }

    def __init__(self):
        self._engine_dir = Path(__file__).resolve().parent
        self._credentials_path = self._engine_dir / "credentials.json"
        self._username = ""
        self._passkey = ""
        self._authorization_header = ""
        self._configuration_error = None
        self._load_credentials()

    def search(self, what, cat="all"):
        if not self._ensure_configured():
            return

        try:
            params, latest_mode = self._build_search_params(what, cat)
            results = self._aggregate_results(params)
        except FileListApiError as error:
            self._log_error("Search failed: %s" % error)
            return

        if not isinstance(results, list):
            self._log_error("Search failed: unexpected API response type '%s'." % type(results).__name__)
            return

        seen_links = set()
        for result in results:
            formatted = self._format_result(result, latest_mode)
            if not formatted:
                continue

            link = formatted.get("link")
            if link in seen_links:
                continue

            seen_links.add(link)
            try:
                prettyPrinter(formatted)
            except BrokenPipeError:
                return

    def download_torrent(self, info):
        if not self._ensure_configured():
            return

        try:
            payload, content_type = self._request_binary(info)
            if self._looks_like_html(payload, content_type) and self._is_filelist_url(info):
                payload, content_type = self._request_binary(info, use_query_auth=True)
        except FileListApiError as error:
            self._log_error("Download failed: %s" % error)
            return

        if self._looks_like_html(payload, content_type):
            self._log_error("Download failed: FileList returned HTML instead of a torrent file.")
            return

        with tempfile.NamedTemporaryFile(suffix=".torrent", delete=False) as handle:
            handle.write(payload)
            print("%s %s" % (handle.name, info))

    def _build_search_params(self, raw_query, cat):
        decoded_query = urllib.parse.unquote_plus(raw_query or "").strip()
        if not decoded_query:
            raise FileListApiError("Empty search query.")

        latest_mode = decoded_query == "." or decoded_query.startswith(". ")
        query_body = decoded_query[1:].strip() if latest_mode else decoded_query
        parsed_query = self._parse_query_tokens(query_body.split())

        params = {"output": "json"}
        category_ids = self.supported_categories.get(cat, self.supported_categories["all"])
        if category_ids and cat != "all":
            params["category"] = category_ids

        if latest_mode:
            params["action"] = "latest-torrents"
            params["limit"] = str(parsed_query["limit"])
            if parsed_query["imdb"]:
                params["imdb"] = parsed_query["imdb"]
            if parsed_query["name_terms"]:
                self._log_error("Latest mode ignores extra terms: %s" % " ".join(parsed_query["name_terms"]))
            return params, True

        params["action"] = "search-torrents"
        params.update(parsed_query["filters"])

        if parsed_query["imdb"]:
            params["type"] = "imdb"
            params["query"] = parsed_query["imdb"]
            if parsed_query["name_query"]:
                params["name"] = parsed_query["name_query"]
        else:
            if not parsed_query["name_query"]:
                raise FileListApiError("Search query is empty after removing filter tokens.")
            params["type"] = "name"
            params["query"] = parsed_query["name_query"]

        return params, False

    def _parse_query_tokens(self, tokens):
        parsed = {
            "filters": {},
            "imdb": None,
            "limit": 100,
            "name_terms": [],
            "name_query": "",
        }

        for token in tokens:
            if not token:
                continue

            key, separator, value = token.partition(":")
            lowered_key = key.lower()

            if separator and lowered_key in FLAG_FILTERS:
                flag_value = self._parse_flag_value(value)
                if flag_value is None:
                    raise FileListApiError("Invalid value for %s filter: %s" % (lowered_key, value))
                parsed["filters"][lowered_key] = flag_value
                continue

            if separator and lowered_key in ("season", "episode"):
                if not value.isdigit():
                    raise FileListApiError("%s must be a positive integer." % lowered_key)
                parsed["filters"][lowered_key] = str(int(value))
                continue

            if separator and lowered_key == "limit":
                if not value.isdigit():
                    raise FileListApiError("limit must be a positive integer.")
                parsed["limit"] = min(max(int(value), 1), 100)
                continue

            season_episode_filters = self._parse_season_episode_token(token)
            if season_episode_filters is not None:
                parsed["filters"].update(season_episode_filters)
                continue

            imdb_value = self._normalize_imdb_token(token)
            if imdb_value and not parsed["imdb"]:
                parsed["imdb"] = imdb_value
                continue

            parsed["name_terms"].append(token)

        parsed["name_query"] = " ".join(parsed["name_terms"]).strip()
        return parsed

    def _parse_flag_value(self, value):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return "1"
        if lowered in ("0", "false", "no", "off"):
            return "0"
        return None

    def _normalize_imdb_token(self, token):
        match = IMDB_RE.match(token.strip())
        if not match:
            return None
        return "tt%s" % match.group(1)

    def _parse_season_episode_token(self, token):
        match = SEASON_EPISODE_RE.match(token.strip())
        if not match:
            return None

        parsed_filters = {"season": str(int(match.group("season")))}
        episode = match.group("episode")
        if episode is not None:
            parsed_filters["episode"] = str(int(episode))

        return parsed_filters

    def _expand_category_requests(self, params):
        category_value = self._coerce_text(params.get("category"))
        if params.get("action") != "search-torrents" or "," not in category_value:
            return [dict(params)]

        expanded_params = []
        for category_id in category_value.split(","):
            normalized_category = category_id.strip()
            if not normalized_category:
                continue

            request_params = dict(params)
            request_params["category"] = normalized_category
            expanded_params.append(request_params)

        if expanded_params:
            return expanded_params
        return [dict(params)]

    def _aggregate_results(self, params):
        aggregated_results = []
        for request_params in self._expand_category_requests(params):
            response = self._request_json(request_params)
            if not isinstance(response, list):
                raise FileListApiError("Unexpected API response type '%s'." % type(response).__name__)
            aggregated_results.extend(response)

        return aggregated_results

    def _request_json(self, params):
        try:
            payload = self._request_text(API_URL, params)
        except FileListApiError as error:
            if error.retry_with_query_auth:
                payload = self._request_text(API_URL, params, use_query_auth=True)
            else:
                raise

        try:
            response = json.loads(payload)
        except ValueError as error:
            raise FileListApiError("Invalid JSON response: %s" % error)

        if isinstance(response, dict) and response.get("error"):
            raise FileListApiError(str(response["error"]))

        return response

    def _request_text(self, url, params, use_query_auth=False):
        response = self._open_request(url, params=params, use_query_auth=use_query_auth)
        return self._decode_payload(response["payload"], response["charset"])

    def _request_binary(self, url, use_query_auth=False):
        response = self._open_request(url, use_query_auth=use_query_auth)
        return response["payload"], response["content_type"]

    def _open_request(self, url, params=None, use_query_auth=False):
        request_url = url
        if params:
            request_params = dict(params)
            if use_query_auth:
                request_params["username"] = self._username
                request_params["passkey"] = self._passkey
            request_url = "%s?%s" % (url, urllib.parse.urlencode(request_params))
        elif use_query_auth and self._is_filelist_url(url):
            request_url = self._append_query_auth(url)

        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": USER_AGENT,
        }
        if self._authorization_header:
            headers["Authorization"] = self._authorization_header

        request = urllib.request.Request(request_url, headers=headers)

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return {
                    "charset": response.headers.get_content_charset() or "utf-8",
                    "content_type": response.headers.get("Content-Type", ""),
                    "payload": response.read(),
                }
        except urllib.error.HTTPError as error:
            error_payload = error.read()
            error_text = self._decode_payload(error_payload, error.headers.get_content_charset() or "utf-8")
            error_message = self._extract_error_message(error_text)
            retry_with_query_auth = (
                self._is_filelist_url(url)
                and not use_query_auth
                and self._should_retry_with_query_auth(error.code, error_message)
            )
            raise FileListApiError(error_message, error.code, retry_with_query_auth)
        except urllib.error.URLError as error:
            raise FileListApiError("Network error: %s" % error.reason)

    def _should_retry_with_query_auth(self, status_code, message):
        if status_code == 401:
            return True
        lowered = (message or "").lower()
        return "username" in lowered or "passkey" in lowered

    def _extract_error_message(self, payload):
        if not payload:
            return "Unexpected empty error response."

        try:
            response = json.loads(payload)
        except ValueError:
            response = None

        if isinstance(response, dict) and response.get("error"):
            return str(response["error"])

        return payload.strip().splitlines()[0] or "Unknown API error."

    def _decode_payload(self, payload, charset):
        return payload.decode(charset or "utf-8", "replace")

    def _append_query_auth(self, url):
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        query_map = dict(query)
        query_map.setdefault("username", self._username)
        query_map.setdefault("passkey", self._passkey)
        updated_query = urllib.parse.urlencode(query_map)
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, updated_query, parsed.fragment))

    def _load_credentials(self):
        if not self._credentials_path.exists():
            self._configuration_error = (
                "Missing credentials.json next to filelist.py. "
                "Copy credentials.json.example to credentials.json and fill in your FileList username and passkey."
            )
            return

        try:
            raw_config = self._credentials_path.read_text(encoding="utf-8")
            config = json.loads(raw_config)
        except OSError as error:
            self._configuration_error = "Unable to read credentials.json: %s" % error
            return
        except ValueError as error:
            self._configuration_error = "Invalid credentials.json: %s" % error
            return

        self._username = str(config.get("username", "")).strip()
        self._passkey = str(config.get("passkey", "")).strip()

        if not self._username or not self._passkey:
            self._configuration_error = "credentials.json must contain non-empty 'username' and 'passkey' values."
            return

        token = "%s:%s" % (self._username, self._passkey)
        encoded = base64.b64encode(token.encode("utf-8")).decode("ascii")
        self._authorization_header = "Basic %s" % encoded

    def _ensure_configured(self):
        if not self._configuration_error:
            return True

        self._log_error(self._configuration_error)
        return False

    def _format_result(self, result, latest_mode):
        if not isinstance(result, dict):
            return None

        link = self._coerce_text(result.get("download_link") or result.get("link"))
        name = self._format_name(result)
        if not link or not name:
            return None

        formatted = {
            "desc_link": self._build_desc_link(result),
            "engine_url": self.url,
            "leech": self._coerce_number(result.get("leechers")),
            "link": link,
            "name": name,
            "pub_date": self._coerce_timestamp(result),
            "seeds": self._coerce_number(result.get("seeders")),
            "size": self._coerce_number(result.get("size")),
        }

        if latest_mode and formatted["pub_date"] == "-1":
            formatted["pub_date"] = self._coerce_timestamp({"added": result.get("upload_date")})

        return formatted

    def _format_name(self, result):
        base_name = self._coerce_text(result.get("name"))
        if not base_name:
            return None

        tags = []
        if self._is_truthy(result.get("freeleech")):
            tags.append("[FREELEECH]")
        if self._is_truthy(result.get("doubleup")):
            tags.append("[DOUBLEUP]")
        if self._is_truthy(result.get("internal")):
            tags.append("[INTERNAL]")

        if not tags:
            return base_name
        return "%s %s" % (" ".join(tags), base_name)

    def _build_desc_link(self, result):
        details_link = self._coerce_text(result.get("details_link"))
        if details_link and details_link.startswith(("http://", "https://")):
            return details_link

        small_description = self._coerce_text(result.get("small_description"))
        if small_description and small_description.startswith(("http://", "https://")):
            return small_description

        torrent_id = result.get("id") or result.get("torrent_id")
        if torrent_id not in (None, ""):
            return "%s/details.php?id=%s" % (self.url, torrent_id)

        return self.url

    def _coerce_timestamp(self, result):
        for key in ("pub_date", "upload_date", "added", "created", "created_at", "uploaded"):
            value = result.get(key)
            timestamp = self._normalize_timestamp(value)
            if timestamp is not None:
                return timestamp
        return "-1"

    def _normalize_timestamp(self, value):
        if value in (None, ""):
            return None

        if isinstance(value, (int, float)):
            numeric = int(value)
            if numeric > 9999999999:
                numeric //= 1000
            return str(numeric)

        text = self._coerce_text(value)
        if not text:
            return None

        if text.isdigit():
            numeric = int(text)
            if numeric > 9999999999:
                numeric //= 1000
            return str(numeric)

        iso_text = text.replace("Z", "+00:00")
        try:
            parsed = datetime.datetime.fromisoformat(iso_text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=datetime.timezone.utc)
            return str(int(parsed.timestamp()))
        except ValueError:
            pass

        for date_format in DATE_FORMATS:
            try:
                parsed = datetime.datetime.strptime(text, date_format)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=datetime.timezone.utc)
                return str(int(parsed.timestamp()))
            except ValueError:
                continue

        return None

    def _coerce_number(self, value):
        if value in (None, ""):
            return "-1"
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)

    def _coerce_text(self, value):
        if value is None:
            return ""
        return str(value).strip()

    def _is_truthy(self, value):
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    def _looks_like_html(self, payload, content_type):
        if not payload:
            return True

        if "text/html" in (content_type or "").lower():
            return True

        prefix = payload[:256].lstrip().lower()
        return prefix.startswith(b"<!doctype") or prefix.startswith(b"<html")

    def _is_filelist_url(self, url):
        host = urllib.parse.urlsplit(url).netloc.lower()
        return host.endswith("filelist.io")

    def _log_error(self, message):
        print("[filelist] %s" % message, file=sys.stderr)

