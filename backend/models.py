from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Repository(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    full_name: str
    html_url: str
    description: str | None = None
    language: str | None = None
    stargazers_count: int
    updated_at: datetime
    archived: bool


class RepositoryPage(BaseModel):
    items: list[Repository]
    page: int
    page_size: int
    total: int


class PaginationState(BaseModel):
    next_url: str | None = None
    previous_url: str | None = None
    first_url: str | None = None
    last_url: str | None = None
