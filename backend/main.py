from fastapi import FastAPI

from config import get_github_token
from logging_setup import configure_logging

logger = configure_logging()

try:
    gh_token = get_github_token()
except RuntimeError:
    gh_token = None
    logger.warning("GitHub token not configured; continuing without authentication. Calls to the GitHub API may be rate-limited.")
else:
    logger.info("GitHub token configured.")

app = FastAPI(title="app")


@app.get("/")
def read_root():
    return {"message": "Hello from app"}
