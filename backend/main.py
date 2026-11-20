from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, Query

from github_client import get_repositories
from models import RepositoryPage

app = FastAPI(title="app")


@app.get("/")
def read_root():
    return {"message": "Hello from app"}


@app.get("/api/orgs/{org}/repos")
async def list_repositories(
    org: str,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> RepositoryPage:
    try:
        repositories = await get_repositories(org)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="GitHub organisation not found.") from exc
        raise HTTPException(status_code=502, detail="GitHub rejected the request.") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Could not reach GitHub.") from exc

    start = (page - 1) * page_size
    return RepositoryPage(
        items=repositories[start : start + page_size],
        page=page,
        page_size=page_size,
        total=len(repositories),
    )
