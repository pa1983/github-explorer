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

## Application logs

Application logs go to stderr as human-readable text by default. Each entry
includes a UTC timestamp, level, logger name, and message. Startup reports
whether a GitHub token is configured without logging its value.

Set `LOG_LEVEL` in `.env` to change the application log level (for example,
`LOG_LEVEL=INFO`). If `LOG_LEVEL` is unset, it defaults to `DEBUG`. Restart the
backend after changing it.

Set `LOG_FORMAT=text` in `.env` for readable logs. Unset or blank values
default to text; unsupported values also fall back to text and log a warning.
To emit one JSON object per log line, set `LOG_FORMAT=json` in `.env` and
restart the backend. A log collector can later forward that stream to Amazon
CloudWatch Logs; this application does not send logs to AWS directly. This
setting does not change Uvicorn's own server or access logs.