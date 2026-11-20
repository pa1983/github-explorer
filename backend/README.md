# Backend

The front end and backend run as foreground development servers. Start them in
separate terminals so one does not block the other.

From the repository root, start the front end with:

```sh
cd frontend && npm run dev
```

From the `backend/` directory, start the backend with:

```sh
uv run uvicorn main:app --reload
```