import os
import unittest
from functools import partial
from unittest.mock import patch

import httpx

from github_client import get_repositories


def repository_payload(repository_id: int) -> dict[str, object]:
    return {
        "id": repository_id,
        "name": f"repository-{repository_id}",
        "full_name": f"example/repository-{repository_id}",
        "html_url": f"https://github.com/example/repository-{repository_id}",
        "description": None,
        "language": "Python",
        "stargazers_count": repository_id,
        "updated_at": "2026-01-01T00:00:00Z",
        "archived": False,
    }


def response(url: str, repository_id: int, link: str | None = None) -> httpx.Response:
    headers = {"Link": link} if link else {}
    return httpx.Response(
        200,
        request=httpx.Request("GET", url),
        headers=headers,
        json=[repository_payload(repository_id)],
    )


class FakeAsyncClient:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = iter(responses)
        self.requests: list[tuple[str, dict[str, str | int] | None]] = []

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def get(
        self, url: str, params: dict[str, str | int] | None = None
    ) -> httpx.Response:
        self.requests.append((url, params))
        return next(self.responses)


class GitHubClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_follows_next_link_and_combines_pages(self) -> None:
        first_url = "https://api.github.com/orgs/example/repos"
        second_url = "https://api.github.com/orgs/example/repos?page=2&per_page=100"
        link = f'<{second_url}>; rel="next", <{second_url}>; rel="last"'
        client = FakeAsyncClient([
            response(first_url, 1, link),
            response(second_url, 2),
        ])

        with patch("github_client.httpx.AsyncClient", return_value=client):
            repositories = await get_repositories("example")

        self.assertEqual([repository.id for repository in repositories], [1, 2])
        self.assertEqual(len(client.requests), 2)
        self.assertEqual(client.requests[0][0], first_url)
        self.assertEqual(client.requests[1], (second_url, None))


if __name__ == "__main__":
    unittest.main()
