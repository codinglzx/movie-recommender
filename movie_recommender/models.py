from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Movie:
    movie_id: int
    title: str
    overview: str
    release_year: Optional[int]
    genres: list[str]
    vote_average: float
    popularity: float
    poster_path: Optional[str] = None
    source: str = "TMDB"

    def genre_text(self) -> str:
        """将 genres 列表转为逗号拼接字符串。"""
        return ','.join(self.genres)


@dataclass
class User:
    """用户类：保存用户基本信息和该用户的评分字典。"""

    user_id: int
    name: str
    ratings: dict[int, float] = field(default_factory=dict)
