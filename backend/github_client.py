import asyncio
import os
import sys
from datetime import UTC, datetime
from urllib.parse import quote

import httpx

from logging_setup import configure_logging
from models import PaginationState, Repository

GITHUB_API_URL = "https://api.github.com"
logger = configure_logging()


async def get_repositories(org: str) -> list[Repository]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-explorer",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url: str | None = f"{GITHUB_API_URL}/orgs/{quote(org, safe='')}/repos"
    params: dict[str, str | int] | None = {"type": "public", "per_page": 100}
    repositories: list[Repository] = []

    async with httpx.AsyncClient(headers=headers, timeout=15) as client:
        while url is not None:
            response = await client.get(url, params=params)
            response.raise_for_status()
            page = [Repository.model_validate(item) for item in response.json()]
            repositories.extend(page)

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
    repositories = await get_repositories(org)
    print(f"Fetched {len(repositories)} repositories for {org}")
    for repository in repositories[:5]:
        print(repository.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
