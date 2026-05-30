import numpy as np
import logging
from movie_recommender import matrix_analyzer

logger = logging.getLogger(__name__)

GENRE_WEIGHT = 2.0
VOTE_WEIGHT = 0.5
POPULARITY_WEIGHT = 0.01


class ContentBasedRecommender:
    def __init__(self, db):
        self.db = db

    def recommend_by_genre_preference(self, user_id: int, top_n: int = 5) -> list[dict]:
        """基于用户高评分电影的类型偏好进行推荐。"""
        user_ratings = self.db.get_user_ratings(user_id)
        if not user_ratings:
            return self._fallback_recommend(top_n)

        # 找出用户高评分电影（>= 4）
        high_rated = {mid: r for mid, r in user_ratings.items() if r >= 4}
        if not high_rated:
            return self._fallback_recommend(top_n, exclude_ids=set(user_ratings))

        # 统计用户偏好类型
        genre_preference = {}
        all_movies = {m.movie_id: m for m in self.db.get_all_movies()}
        for movie_id, rating in high_rated.items():
            if movie_id not in all_movies:
                continue
            movie = all_movies[movie_id]
            for genre in movie.genres:
                genre_preference[genre] = genre_preference.get(genre, 0) + rating / 5

        if not genre_preference:
            return self._fallback_recommend(top_n, exclude_ids=set(user_ratings))

        # 对用户未评分电影计算推荐分数
        candidates = []
        for movie in all_movies.values():
            if movie.movie_id in user_ratings:
                continue
            genre_score = sum(genre_preference.get(g, 0) for g in movie.genres)
            if genre_score == 0:
                continue
            score = genre_score * GENRE_WEIGHT + movie.vote_average * VOTE_WEIGHT + movie.popularity * POPULARITY_WEIGHT
            candidates.append({'movie': movie, 'score': round(score, 2), 'method': 'genre_preference'})

        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:top_n]

    def _fallback_recommend(self, top_n: int, exclude_ids: set[int] = None) -> list[dict]:
        """当用户无评分或偏好难以确定时，推荐高评分高热度电影。"""
        exclude_ids = exclude_ids or set()
        all_movies = self.db.get_all_movies()
        scored = [
            {'movie': m, 'score': m.vote_average * VOTE_WEIGHT + m.popularity * POPULARITY_WEIGHT,
             'method': 'fallback'}
            for m in all_movies
            if m.movie_id not in exclude_ids
        ]
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_n]

class CollaborativeFilteringRecommender:
    def __init__(self, db):
        self.db = db

    def recommend_by_collaborative_filtering(self, user_id: int, top_n: int = 5) -> list[dict]:
        """基于用户余弦相似度的协同过滤推荐。"""
        matrix, user_ids, movie_ids = self._build_rating_matrix()
        if user_id not in user_ids:
            logger.warning(f"用户 {user_id} 不在评分矩阵中，使用 fallback 推荐")
            return self._fallback_cf_recommend(top_n)

        user_idx = user_ids.index(user_id)
        user_vec = matrix[user_idx]

        # 计算与所有其他用户的相似度
        similarities = []
        for i, uid in enumerate(user_ids):
            if i != user_idx:
                sim = self._cosine_similarity(user_vec, matrix[i])
                if sim > 0:
                    similarities.append((i, sim))
        similarities.sort(key=lambda x: x[1], reverse=True)

        # 预测未评分电影的评分
        predictions = {}
        for movie_idx in range(len(movie_ids)):
            if user_vec[movie_idx] == 0:
                numerator, denominator = 0.0, 0.0
                for sim_user_idx, sim in similarities[:10]:
                    other_rating = matrix[sim_user_idx, movie_idx]
                    if other_rating > 0:
                        numerator += sim * other_rating
                        denominator += abs(sim)
                if denominator > 0:
                    predictions[movie_idx] = numerator / denominator

        if not predictions:
            return self._fallback_cf_recommend(top_n, user_id=user_id)

        sorted_pred = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
        all_movies = {m.movie_id: m for m in self.db.get_all_movies()}
        recommendations = []
        for movie_idx, score in sorted_pred[:top_n]:
            movie_id = movie_ids[movie_idx]
            if movie_id in all_movies:
                recommendations.append({
                    'movie': all_movies[movie_id],
                    'score': round(score, 2),
                    'method': 'collaborative_filtering'
                })
        return recommendations

    def _build_rating_matrix(self):
        """构建用户-电影评分矩阵。"""
        ratings = self.db.get_all_user_ratings()
        users = self.db.get_all_users()
        movies = self.db.get_all_movies()
        if not users or not movies:
            return np.array([]), [], []
        return matrix_analyzer.build_rating_matrix(users, movies, ratings)

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """计算两个评分向量之间的余弦相似度。"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _fallback_cf_recommend(self, top_n: int, user_id: int = None) -> list[dict]:
        """当协同过滤无法产生结果时，推荐热门电影。"""
        rated_movie_ids = set(self.db.get_user_ratings(user_id)) if user_id is not None else set()
        all_movies = self.db.get_all_movies()
        scored = [
            {'movie': m, 'score': m.vote_average, 'method': 'collaborative_filtering_fallback'}
            for m in all_movies
            if m.movie_id not in rated_movie_ids
        ]
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_n]


class Recommender:
    """统一推荐入口，明确对应项目要求中的 Recommender 类。"""

    def __init__(self, db):
        self.db = db
        self.content = ContentBasedRecommender(db)
        self.collaborative = CollaborativeFilteringRecommender(db)

    def recommend_by_genre(self, user_id: int, top_n: int = 5) -> list[dict]:
        return self.content.recommend_by_genre_preference(user_id, top_n)

    def recommend_collaborative(self, user_id: int, top_n: int = 5) -> list[dict]:
        return self.collaborative.recommend_by_collaborative_filtering(user_id, top_n)

    def build_rating_matrix(self):
        return self.collaborative._build_rating_matrix()

    def analyze_rating_matrix(self) -> dict:
        matrix, user_ids, movie_ids = self.build_rating_matrix()
        analysis = matrix_analyzer.analyze_rating_matrix(matrix)
        analysis.update({
            'matrix': matrix,
            'user_ids': user_ids,
            'movie_ids': movie_ids,
        })
        return analysis
