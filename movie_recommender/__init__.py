"""Movie Recommender — 电影数据分析与推荐系统。

公开 API：
- ``Movie`` / ``User``  : 数据模型
- ``Database``          : SQLite 持久化
- ``RecommenderEngine`` : 统一推荐入口
"""

from movie_recommender.models import Movie, User
from movie_recommender.database import Database
from movie_recommender.recommender import RecommenderEngine

__all__ = ["Movie", "User", "Database", "RecommenderEngine"]
__version__ = "1.0.0"
