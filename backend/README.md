# Backend

The front end and backend run as foreground development servers. Start them in
separate terminals so one does not block the other.

From the repository root, start the front end with:

```sh
cd frontend && npm run dev
```

From the `backend/` directory, start the backend with:

```sh
uv run uvicorn main:app --reload --env-file .env
```

Replace the placeholder in `backend/.env` with your GitHub token. The backend
process receives it as the `GITHUB_TOKEN` environment variable. Keep the file
local; `.env` files are ignored by Git.

To confirm the token loads from `.env` without printing it, run this from the
`backend/` directory:

```sh
env -u GITHUB_TOKEN uv run --env-file .env python -m config
```

To test the GitHub client directly, open `github_client.py` in VS Code and use
**Run Python File**, or run this from `backend/`. The runner loads `.env` from
next to the script without overriding environment variables that are already
set, and fetches at most three pages for the given organization:

```sh
uv run python -m github_client google
```

To also apply `LOG_LEVEL` and `LOG_FORMAT` from `.env`, use
`uv run --env-file .env python -m github_client google` so the settings are
available before the logger is configured.

## Check the API route

With the backend running, use a small organisation (e.g. fastapi) to check the integration:

```sh
curl -f 'http://127.0.0.1:8000/api/orgs/psf/repos?language=python&min_stars=10&archived=false&sort=stars&order=desc&page=1&page_size=25'
```

The response contains `items`, `page`, `page_size`, and `total`. Pages start at
1; the default page size is 25 and the maximum is 100. A page beyond the end
returns an empty `items` array. `total` counts all matching repositories before
pagination. Use `page * page_size < total` to check whether there is another page.

| Parameter | Behavior |
| --- | --- |
| `language` | Omit for all languages, pass a name for a case-insensitive match, or pass `language=` for repositories with no primary language. |
| `min_stars` | Inclusive non-negative minimum; defaults to `0`. |
| `archived` | Pass `true` for archived or `false` for non-archived repositories. Omit for both. |
| `sort` | `name` (default, case-insensitive), `stars`, or `updated`. |
| `order` | `asc` (default) or `desc`. Ties always use ascending repository ID. |

Missing, empty, and whitespace-only descriptions and languages are returned as
`null`. The supported sort fields (name, stars, last updated) are required and
non-null; if a nullable sort field is added, missing values should sort last
in both directions.

On a cache miss, the route fetches all GitHub pages and caches the full list
for one hour per organisation. Each request filters and sorts a separate list
before slicing it, so changes to filters, sorting, or page reuse the same
cached data. The in-memory cache
holds up to 32 organisations per process; it is not shared across workers
and is cleared on restart. Failed fetches are not cached, and simultaneous
misses can fetch the same organisation more than once.

The three-page limit applies only to the standalone runner.

### GitHub rate limits

If GitHub rate-limits a request, the API returns HTTP `429`. The response's
`detail` field is plain text intended for direct display:

```json
{"detail": "GitHub's rate limit has been reached. Please try again in 3 minutes."}
```

The `Retry-After` header gives the wait in seconds. The API uses GitHub's
`Retry-After` and, when the primary quota is exhausted, `X-RateLimit-Reset`.
It uses the longer delay if both apply, rounds up to whole minutes for the
message, and recommends one minute if no usable timing is supplied. The backend
does not retry automatically.

## Application logs

Application logs go to stderr as human-readable text by default. Each entry
includes a UTC timestamp, level, logger name, and message. When fetching
repositories, the GitHub client logs at `INFO` whether it applied the token,
without logging its value.

Set `LOG_LEVEL` in `.env` to change the application log level (for example,
`LOG_LEVEL=INFO`). If `LOG_LEVEL` is unset, it defaults to `DEBUG`. Restart the
backend after changing it.

Set `LOG_FORMAT=text` in `.env` for readable logs. Unset or blank values
default to text; unsupported values also fall back to text and log a warning.
To emit one JSON object per log line, set `LOG_FORMAT=json` in `.env` and
restart the backend. A log collector can later forward that stream to Amazon
CloudWatch Logs; this application does not send logs to AWS directly. This
setting does not change Uvicorn's own server or access logs.


## Implementation Notes
# httpx
Using HTTPX in favour of requests to allow for future use of async 
