import unittest
from unittest.mock import patch

import httpx

from cache import TTLCache
from github_client import get_repositories
from main import app
from models import Repository


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


class RepositoryCacheTest(unittest.IsolatedAsyncioTestCase):
    async def test_pages_share_the_cache_until_it_expires(self) -> None:
        first = Repository.model_validate(repository_payload(1))
        second = Repository.model_validate(repository_payload(2))
        updated = Repository.model_validate(repository_payload(3))

        with (
            patch("main.repository_cache", TTLCache[list[Repository]](300, 32)),
            patch("cache.monotonic", return_value=100) as clock,
            patch("main.get_repositories", side_effect=[[first, second], [updated]]) as fetch,
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as api:
                page_one = await api.get("/api/orgs/example/repos?page_size=1")
                clock.return_value = 399
                page_two = await api.get("/api/orgs/Example/repos?page=2&page_size=1")
                fetch.assert_awaited_once_with("example")

                clock.return_value = 400
                refreshed = await api.get("/api/orgs/example/repos?page_size=1")

        self.assertEqual(fetch.await_count, 2)
        for result, repository_id, total in (
            (page_one, 1, 2),
            (page_two, 2, 2),
            (refreshed, 3, 1),
        ):
            self.assertEqual(result.status_code, 200)
            self.assertEqual([repo["id"] for repo in result.json()["items"]], [repository_id])
            self.assertEqual(result.json()["total"], total)


class RepositoryQueryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.api = await self.enterAsyncContext(httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ))
        self.url = "/api/orgs/example/repos"

    def stub_repositories(self, *rows: tuple[int, dict[str, object]]) -> list[Repository]:
        repositories = [
            Repository.model_validate(repository_payload(repo_id) | overrides)
            for repo_id, overrides in rows
        ]
        self.enterContext(patch("main.repository_cache", TTLCache[list[Repository]](300, 32)))
        self.fetch = self.enterContext(patch("main.get_repositories", return_value=repositories))
        return repositories

    async def test_empty_language_filter_matches_null_and_blank_only(self) -> None:
        self.stub_repositories(
            (1, {"language": None}),
            (2, {"language": " \t", "description": ""}),
            (3, {"language": " Python "}),
        )

        missing = await self.api.get(self.url, params={"language": ""})
        named = await self.api.get(self.url, params={"language": "pYTHon"})

        self.assertEqual(missing.status_code, 200)
        self.assertEqual(named.status_code, 200)
        self.assertEqual(missing.json()["total"], 2)
        self.assertEqual(
            [(repo["id"], repo["language"], repo["description"]) for repo in missing.json()["items"]],
            [(1, None, None), (2, None, None)],
        )
        self.assertEqual([repo["id"] for repo in named.json()["items"]], [3])

    async def test_filters_and_sorts_before_slicing_without_changing_cache(self) -> None:
        repositories = self.stub_repositories(
            (10, {"archived": True}),
            (9, {"language": "Go"}),
            (1, {}),
            (5, {"stargazers_count": 8}),
            (4, {"stargazers_count": 8}),
            (3, {}),
        )
        params = dict(language="python", min_stars=3, archived="false", sort="stars", order="desc", page_size=2)

        for page, expected_ids in ((1, [4, 5]), (2, [3]), (3, [])):
            with self.subTest(page=page):
                result = await self.api.get(self.url, params=params | {"page": page})
                self.assertEqual(result.status_code, 200)
                body = result.json()
                self.assertEqual([repo["id"] for repo in body["items"]], expected_ids)
                self.assertEqual((body["page"], body["page_size"], body["total"]), (page, 2, 3))

        self.fetch.assert_awaited_once_with("example")
        self.assertEqual([repo.id for repo in repositories], [10, 9, 1, 5, 4, 3])

    async def test_name_and_updated_sorting_are_independent(self) -> None:
        self.stub_repositories(
            (1, {"name": "beta", "updated_at": "2026-03-01T00:00:00Z"}),
            (2, {"name": "Alpha", "updated_at": "2026-02-01T00:00:00Z"}),
            (3, {"name": "Zulu", "updated_at": "2026-01-01T00:00:00Z"}),
        )
        for sort, order, expected_ids in (
            ("name", "asc", [2, 1, 3]),
            ("name", "desc", [3, 1, 2]),
            ("updated", "asc", [3, 2, 1]),
            ("updated", "desc", [1, 2, 3]),
        ):
            with self.subTest(sort=sort, order=order):
                result = await self.api.get(self.url, params={"sort": sort, "order": order})
                self.assertEqual(result.status_code, 200)
                self.assertEqual([repo["id"] for repo in result.json()["items"]], expected_ids)


if __name__ == "__main__":
    unittest.main()
