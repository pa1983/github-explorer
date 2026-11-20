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
curl -f 'http://127.0.0.1:8000/api/orgs/psf/repos?page=1&page_size=25'
```

The response contains `items`, `page`, `page_size`, and `total`. Pages start at
1; the default page size is 25 and the maximum is 100. A page beyond the end
returns an empty `items` array. Use `page * page_size < total` to check whether
there is another page.

The route still fetches all GitHub pages on each request before slicing the
results. The three-page limit applies only to the standalone runner. Filtering
and sorting are not implemented yet.

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
