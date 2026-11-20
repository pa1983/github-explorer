from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, Query

from cache import TTLCache
from github_client import get_repositories
from logging_setup import configure_logging
from models import Repository, RepositoryPage
from repository_query import SortField, SortOrder, query_repositories

logger = configure_logging()
app = FastAPI(title="app")

CACHE_TTL_SECONDS = 3600
CACHE_MAX_ORGS = 32
repository_cache = TTLCache[list[Repository]](CACHE_TTL_SECONDS, CACHE_MAX_ORGS)


async def get_cached_repositories(org: str) -> list[Repository]:
    """
    Get the list of repositories for the given organization from the cache if available.
    If not cached, fetch from GitHub and store in the cache.

    Args:
        org (str): The GitHub organization name.

    Returns:
        list[Repository]: The list of repositories for the organization.
    """
    # TODO - if time, come back and add handling for duplicate requests to avoid multiple concurrent fetches for the same org
    #  TODO - need to consider handling cache population if hit api limit - background process to 
    # pick up the cache population later when the API limit allows and prevent subsequent calls for same 
    # org.  Also, for cache invalidations, consider returning old data if available while triggering a refresh. 
    # Would need to add a message to user.  Perhaps a status field indicating the age of the displayed data and a note that it's stale? 
    key = org.lower()
    cached = repository_cache.get(key)
    if cached is not None:
        logger.debug(f"Cache hit for organization: {key}")
        return cached
    else:
        logger.debug(f"Cache miss for organization: {key}")

    repositories = await get_repositories(org)
    repository_cache.set(key, repositories)
    return repositories


@app.get("/")
def read_root():
    return {"message": "Hello from app"}


@app.get("/api/orgs/{org}/repos")
async def list_repositories(
    org: str,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    language: Annotated[str | None, Query(description="Primary language; empty matches no language.")] = None,
    min_stars: Annotated[int, Query(ge=0)] = 0,
    archived: bool | None = None,
    sort: SortField = "name",
    order: SortOrder = "asc",
) -> RepositoryPage:
    try:
        repositories = await get_cached_repositories(org)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="GitHub organisation not found.") from exc
        raise HTTPException(status_code=502, detail="GitHub rejected the request.") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Could not reach GitHub.") from exc

    matches = query_repositories(
        repositories, language=language, min_stars=min_stars, archived=archived, sort=sort, order=order
    )
    start = (page - 1) * page_size
    return RepositoryPage(
        items=matches[start : start + page_size],
        page=page,
        page_size=page_size,
        total=len(matches),
    )
