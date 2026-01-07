from enum import Enum
from pydantic import BaseModel


class SourceType(str, Enum):
    RSS = "rss"


class Source(BaseModel):
    id: str
    name: str
    type: SourceType
    url: str
    category: str
    enabled: bool = True
