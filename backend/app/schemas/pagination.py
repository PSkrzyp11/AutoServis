from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True)
class PageParams:
    limit: int
    offset: int


class Page[ItemT](BaseModel):
    items: list[ItemT]
    total: int = Field(description="Total number of items matching the filters")
    limit: int = Field(description="Maximum number of items returned in this page")
    offset: int = Field(description="Number of items skipped before this page")
