import numpy as np
import logging
from dataclasses import dataclass, asdict
from typing import Optional
from movie_recommender import matrix_analyzer
from movie_recommender.algorithms import (
    cosine_similarity,
    genre_preference_score,
    score_movie_by_genre,
)

logger = logging.getLogger(__name__)

# 类型匹配、电影均分、热度的统一权重。
# 同时供个性化推荐和 fallback 使用,保证两路推荐在没有偏好数据时
# 排序口径完全一致(都是"按均分+热度"排)。
GENRE_WEIGHT = 2.0
VOTE_WEIGHT = 0.5
POPULARITY_WEIGHT = 0.01


def _fallback_score(movie) -> float:
    """fallback 场景:无用户偏好时,只按均分+热度排序(传空偏好给 score_movie_by_genre)。"""
    return score_movie_by_genre(
        movie, {},
        genre_weight=GENRE_WEIGHT,
        vote_weight=VOTE_WEIGHT,
        popularity_weight=POPULARITY_WEIGHT,
    )


@dataclass
class RecommenderStatus:
    """推荐可用性状态 — 模板用 asdict() 渲染成 JSON 喂给前端 toast/按钮。"""
    available: bool
    reason: Optional[str] = None
    message: Optional[str] = None
    cta_text: Optional[str] = None
    cta_href: Optional[str] = None
    cta_icon: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


_NO_RATINGS = RecommenderStatus(
    available=False, reason='no_ratings',
    message='你还没有给任何电影评分。开始记录你的喜好，系统会基于你的口味推荐同类型佳作。',
    cta_text='去评分', cta_href='/movies', cta_icon='sparkle',
)

_NO_RATINGS_FOR_CF = RecommenderStatus(
    available=False, reason='no_ratings',
    message='至少需要 1 次评分，系统才能找到与你口味相似的用户。',
    cta_text='去评分', cta_href='/movies', cta_icon='sparkle',
)

_NO_HIGH_RATINGS = RecommenderStatus(
    available=False, reason='no_high_ratings',
    message='还没有 4 星以上的评分。给真正喜欢的电影 4 星以上，系统才能识别你的口味偏好。',
    cta_text='调整评分', cta_href='/movies', cta_icon='star',
)

_NO_OTHER_USERS = RecommenderStatus(
    available=False, reason='no_other_users',
    message='需要其他用户也参与评分，才能用协同过滤为你推荐。先记下你的喜好，等更多用户加入即可解锁。',
    cta_text='记下我的喜好', cta_href='/movies', cta_icon='user',
)

_AVAILABLE = RecommenderStatus(available=True)


class ContentBasedRecommender:
    def __init__(self, db):
        self.db = db

    def recommend_by_genre_preference(self, user_id: int, top_n: int = 5) -> list[dict]:
        """基于用户高评分电影的类型偏好进行推荐。"""
        if self.db.get_user(user_id) is None:
            raise ValueError(f"用户 {user_id} 不存在")
        user_ratings = self.db.get_user_ratings(user_id)
        if not user_ratings:
            return self._fallback_recommend(top_n)

        # 找出用户高评分电影（>= 4）
        high_rated = {mid: r for mid, r in user_ratings.items() if r >= 4}
        if not high_rated:
            return self._fallback_recommend(top_n, exclude_ids=set(user_ratings))

        # 调用函数封装：算出用户类型偏好
        all_movies = {m.movie_id: m for m in self.db.get_all_movies()}
        genre_preference = genre_preference_score(user_ratings, all_movies, min_rating=4.0)

        if not genre_preference:
            return self._fallback_recommend(top_n, exclude_ids=set(user_ratings))

        # 对用户未评分电影计算推荐分数 — 调用函数封装
        # 排除"无任何偏好类型命中"的电影(避免 fallback 风格的电影混进来)
        candidates = []
        for movie in all_movies.values():
            if movie.movie_id in user_ratings:
                continue
            # 命中任一偏好类型才能进推荐
            if not any(genre_preference.get(g, 0) > 0 for g in movie.genres):
                continue
            score = score_movie_by_genre(movie, genre_preference,
                                        genre_weight=GENRE_WEIGHT,
                                        vote_weight=VOTE_WEIGHT,
                                        popularity_weight=POPULARITY_WEIGHT)
            candidates.append({'movie': movie, 'score': round(score, 2), 'method': 'genre_preference'})

        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:top_n]

    def _fallback_recommend(self, top_n: int, exclude_ids: set[int] = None) -> list[dict]:
        """当用户无评分或偏好难以确定时,推荐高评分高热度电影(与个性化推荐共享公式)。"""
        exclude_ids = exclude_ids or set()
        all_movies = self.db.get_all_movies()
        scored = [
            {'movie': m, 'score': round(_fallback_score(m), 2), 'method': 'fallback'}
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
        if self.db.get_user(user_id) is None:
            raise ValueError(f"用户 {user_id} 不存在")
        matrix, user_ids, movie_ids = self._build_rating_matrix()
        user_id_to_idx, _ = matrix_analyzer.build_index_maps(user_ids, movie_ids)
        user_idx = user_id_to_idx.get(user_id)
        if user_idx is None:
            # 用户存在但还没评分 → 评分矩阵里没他这一行,走 fallback 推热门
            logger.info(f"用户 {user_id} 暂无评分数据，CF 走 fallback")
            return self._fallback_cf_recommend(top_n)

        user_vec = matrix[user_idx]

        # 计算与所有其他用户的相似度（调用 algorithms.cosine_similarity）
        similarities = []
        for i, uid in enumerate(user_ids):
            if i != user_idx:
                sim = cosine_similarity(user_vec, matrix[i])
                if sim > 0:
                    similarities.append((i, sim))
        similarities.sort(key=lambda x: x[1], reverse=True)

        # 没有相似用户 → fallback
        if not similarities:
            return self._fallback_cf_recommend(top_n, user_id=user_id)

        # 预测未评分电影的评分 — 向量化版本(等价于对每部电影调用 algorithms.predict_rating_cf,
        # 但用 numpy 广播一次性算所有电影,避免 Python 循环)。
        # 用 numpy fancy indexing 一次性取 top-K 用户对所有未评分电影的评价
        top_user_idxs = np.array([idx for idx, _ in similarities[:10]])
        top_sim_values = np.array([sim for _, sim in similarities[:10]])
        unrated_movie_idxs = np.where(user_vec == 0)[0]
        # shape: (K, U) — top-K 用户对所有未评分电影的评分
        similar_ratings = matrix[np.ix_(top_user_idxs, unrated_movie_idxs)]

        # 一次性算所有未评分电影的预测分(避免逐电影循环)
        rated_mask = similar_ratings > 0
        num = np.zeros(len(unrated_movie_idxs))
        den = np.zeros(len(unrated_movie_idxs))
        for k in range(len(top_user_idxs)):
            r_k = similar_ratings[k]
            n_k = r_k * top_sim_values[k]
            num += np.where(rated_mask[k], n_k, 0)
            den += np.where(rated_mask[k], np.abs(top_sim_values[k]), 0)
        with np.errstate(divide='ignore', invalid='ignore'):
            preds = np.where(den > 0, num / den, 0)

        predictions = {
            int(idx): float(score)
            for idx, score in zip(unrated_movie_idxs, preds)
            if score > 0
        }

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

    def _fallback_cf_recommend(self, top_n: int, user_id: int = None) -> list[dict]:
        """当协同过滤无法产生结果时,推荐热门电影(与类型偏好的 fallback 共享同一种排序口径)。"""
        rated_movie_ids = set(self.db.get_user_ratings(user_id)) if user_id is not None else set()
        all_movies = self.db.get_all_movies()
        scored = [
            {
                'movie': m,
                'score': round(_fallback_score(m), 2),
                'method': 'collaborative_filtering_fallback',
            }
            for m in all_movies
            if m.movie_id not in rated_movie_ids
        ]
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_n]


class RecommenderEngine:
    """统一推荐入口，明确对应项目要求中的 Recommender 类。"""

    def __init__(self, db):
        self.db = db
        self.content = ContentBasedRecommender(db)
        self.collaborative = CollaborativeFilteringRecommender(db)

    def recommend_by_genre(self, user_id: int, top_n: int = 5) -> list[dict]:
        return self.content.recommend_by_genre_preference(user_id, top_n)

    def recommend_collaborative(self, user_id: int, top_n: int = 5) -> list[dict]:
        return self.collaborative.recommend_by_collaborative_filtering(user_id, top_n)

    def genre_recommendation_status(self, user_id: int) -> dict:
        """判断基于类型偏好的推荐是否可用。

        返回值结构(供模板渲染):
            available : bool      # True = 有数据可生成个性化推荐
            reason    : str|None  # 'no_ratings' / 'no_high_ratings' / None
            message   : str|None  # 人类可读的友好提示
            cta_text  : str|None  # 引导按钮文案
            cta_href  : str|None  # 引导按钮链接
            cta_icon  : str|None  # 引导按钮图标
        """
        if not self.db.get_user_ratings(user_id):
            return _NO_RATINGS.to_dict()
        high_rated = {mid: r for mid, r in self.db.get_user_ratings(user_id).items() if r >= 4}
        if not high_rated:
            return _NO_HIGH_RATINGS.to_dict()
        return _AVAILABLE.to_dict()

    def collaborative_recommendation_status(self, user_id: int) -> dict:
        """判断协同过滤推荐是否可用(用 O(1) count 查询,不构建矩阵)。"""
        if not self.db.get_user_ratings(user_id):
            return _NO_RATINGS_FOR_CF.to_dict()
        # COUNT(DISTINCT user_id) 比 build_rating_matrix 便宜得多
        if self.db.count_users_with_ratings() <= 1:
            return _NO_OTHER_USERS.to_dict()
        return _AVAILABLE.to_dict()

    def build_rating_matrix(self):
        return self.collaborative._build_rating_matrix()

    def analyze_rating_matrix(self) -> dict:
        matrix, user_ids, movie_ids = self.build_rating_matrix()
        analysis = matrix_analyzer.analyze_rating_matrix(matrix)
        user_id_to_idx, movie_id_to_idx = matrix_analyzer.build_index_maps(user_ids, movie_ids)
        analysis.update({
            'matrix': matrix,
            'user_ids': user_ids,
            'movie_ids': movie_ids,
            'user_id_to_idx': user_id_to_idx,
            'movie_id_to_idx': movie_id_to_idx,
        })
        return analysis
