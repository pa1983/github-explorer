from typing import Literal

from models import Repository

type SortField = Literal["stars", "updated", "name"]
type SortOrder = Literal["asc", "desc"]


def query_repositories(
    repositories: list[Repository],
    *,
    language: str | None,
    min_stars: int,
    archived: bool | None,
    sort: SortField,
    order: SortOrder,
) -> list[Repository]:
    language_key = language.strip().lower() if language is not None else None
    matches = [
        repo
        for repo in repositories
        if (language_key is None or (repo.language or "").lower() == language_key)
        and repo.stargazers_count >= min_stars
        and (archived is None or repo.archived == archived)
    ]

    # Stable sorts keep IDs ascending on ties, even when the primary sort is descending.
    matches.sort(key=lambda repo: repo.id)
    descending = order == "desc"
    if sort == "stars":
        matches.sort(key=lambda repo: repo.stargazers_count, reverse=descending)
    elif sort == "updated":
        matches.sort(key=lambda repo: repo.updated_at, reverse=descending)
    else:
        matches.sort(key=lambda repo: repo.name.lower(), reverse=descending)
    return matches
