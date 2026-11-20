import asyncio
import sys
from datetime import UTC, datetime
from urllib.parse import quote

import httpx

from config import get_github_token
from logging_setup import configure_logging
from models import PaginationState, Repository

GITHUB_API_URL = "https://api.github.com"
logger = configure_logging()


async def get_repositories(
    org: str, *, max_pages: int | None = None
) -> list[Repository]:
    """
    Fetch public repositories for a given GitHub organisation.

    Args:
        org: The GitHub organization name.
        max_pages: The maximum number of pages to fetch, useful for limiting API 
        requests during development. If None, fetch all pages.

    Returns:
        A list of Repository objects.

    Raises:
        ValueError: If max_pages is less than 1.
    """
    if max_pages is not None and max_pages < 1:
        raise ValueError("max_pages must be at least 1")

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-explorer",
    }
    try:
        token = get_github_token()
    except RuntimeError:
        logger.info("GitHub token not configured; proceeding without an Authorization header.")
    else:
        headers["Authorization"] = f"Bearer {token}"
        logger.info("GitHub bearer token applied to the Authorization header.")

    url: str | None = f"{GITHUB_API_URL}/orgs/{quote(org, safe='')}/repos"
    params: dict[str, str | int] | None = {"type": "public", "per_page": 100}
    repositories: list[Repository] = []
    pages_fetched = 0

    async with httpx.AsyncClient(headers=headers, timeout=15) as client:
        while url is not None:
            response = await client.get(url, params=params)
            response.raise_for_status()
            page = [Repository.model_validate(item) for item in response.json()]
            repositories.extend(page)
            pages_fetched += 1

            pagination = PaginationState(
                next_url=response.links.get("next", {}).get("url"),
                previous_url=response.links.get("prev", {}).get("url"),
                first_url=response.links.get("first", {}).get("url"),
                last_url=response.links.get("last", {}).get("url"),
            )
            logger.debug(
                "GitHub GET succeeded: url=%s status=%d repositories=%d "
                "remaining=%s reset_in_seconds=%s",
                response.url,
                response.status_code,
                len(page),
                response.headers.get("x-ratelimit-remaining", "unknown"),
                _seconds_until_reset(response),
            )
            if max_pages is not None and pages_fetched >= max_pages:
                break

            url = pagination.next_url
            params = None  # GitHub's next URL already contains the query parameters.

    return repositories


def _seconds_until_reset(response: httpx.Response) -> int | str:
    reset = response.headers.get("x-ratelimit-reset")
    if reset is None:
        return "unknown"
    try:
        return max(0, int(int(reset) - datetime.now(UTC).timestamp()))
    except ValueError:
        return "unknown"


async def main() -> None:
    org = sys.argv[1] if len(sys.argv) > 1 else "google"
    repositories = await get_repositories(org, max_pages=3)
    print(f"Fetched {len(repositories)} repositories for {org}")
    for repository in repositories[:5]:
        print(repository.model_dump_json(indent=2))


if __name__ == "__main__":
    # Adding support for loading environment variables from a .env file to allow for local development
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"), override=False)
    asyncio.run(main())
