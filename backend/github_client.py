import asyncio
import os
import sys
from urllib.parse import quote

import httpx

from models import Repository

GITHUB_API_URL = "https://api.github.com"


async def get_repositories(org: str) -> list[Repository]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-explorer",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(headers=headers, timeout=15) as client:
        response = await client.get(
            f"{GITHUB_API_URL}/orgs/{quote(org, safe='')}/repos",
            params={"type": "public", "per_page": 100},
        )
        response.raise_for_status()

    return [Repository.model_validate(item) for item in response.json()]


async def main() -> None:
    org = sys.argv[1] if len(sys.argv) > 1 else "google"
    repositories = await get_repositories(org)
    print(f"Fetched {len(repositories)} repositories for {org}")
    for repository in repositories[:5]:
        print(repository.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
