"""推荐算法核心函数 — 函数封装层。

这些是纯函数,可独立测试/复用。``recommender.py`` 中的策略类
只是把这些函数组织起来,核心数学/统计逻辑都在这里。

注意:评分矩阵的构建仍由 ``matrix_analyzer.build_rating_matrix``
负责(因为它返回 matrix + user_ids + movie_ids 三个相关输出),
本模块只放纯函数。
"""
from typing import Dict
import numpy as np


# ========== 协同过滤核心公式 ==========
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """两个向量的余弦相似度。

    公式: cos(A, B) = (A · B) / (||A|| × ||B||)
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def predict_rating_cf(similar_ratings: np.ndarray,
                     similarities: np.ndarray) -> float:
    """协同过滤 — 用相似用户的加权评分预测当前用户对某部电影的评分。

    公式:
        predicted = Σ(similarity × other_rating) / Σ|similarity|

    Args:
        similar_ratings: (K,) K 个最相似用户对**同一部电影**的评分(0=未评分)
        similarities: (K,) 这 K 个相似用户与当前用户的余弦相似度

    Returns:
        预测评分(浮点数),若无可用相似用户则返回 0.0
    """
    mask = similar_ratings > 0
    if not mask.any():
        return 0.0
    num = np.dot(similar_ratings[mask], similarities[mask])
    den = np.abs(similarities[mask]).sum()
    return float(num / den) if den > 0 else 0.0


# ========== 基于类型偏好的核心公式 ==========
def genre_preference_score(user_ratings: Dict[int, float],
                           all_movies: Dict[int, 'Movie'],
                           min_rating: float = 4.0) -> Dict[str, float]:
    """计算用户对各类型的偏好分(只统计 min_rating 以上的电影)。

    公式:
        genre_score[genre] = Σ(rating / 5) for movie in high_rated
        归一化到 [0, 1] 区间

    Args:
        user_ratings: {movie_id: rating} 当前用户的评分字典
        all_movies: {movie_id: Movie} 所有电影字典
        min_rating: 计入偏好的最低评分(默认 4)

    Returns:
        {genre_name: preference_score} 偏好分字典
    """
    high_rated = {mid: r for mid, r in user_ratings.items() if r >= min_rating}
    if not high_rated:
        return {}

    raw: Dict[str, float] = {}
    for movie_id, rating in high_rated.items():
        movie = all_movies.get(movie_id)
        if not movie:
            continue
        for genre in movie.genres:
            raw[genre] = raw.get(genre, 0.0) + rating / 5.0

    # 归一化: 偏好分除以该用户可能拿到的最大分
    max_possible = sum(r / 5.0 for r in high_rated.values())
    if max_possible == 0:
        return {}
    return {g: round(v / max_possible, 4) for g, v in raw.items()}


def score_movie_by_genre(movie: 'Movie',
                         genre_preference: Dict[str, float],
                         genre_weight: float = 2.0,
                         vote_weight: float = 0.5,
                         popularity_weight: float = 0.01) -> float:
    """为某部电影算"类型匹配分"。

    公式:
        score = genre_match × genre_weight + vote_average × vote_weight + popularity × popularity_weight

    Args:
        movie: 候选电影
        genre_preference: {genre: score} 用户偏好字典
        genre_weight: 类型匹配权重
        vote_weight: vote_average 权重
        popularity_weight: popularity 权重

    Returns:
        电影综合分
    """
    genre_match = sum(genre_preference.get(g, 0.0) for g in movie.genres)
    return (
        genre_match * genre_weight
        + movie.vote_average * vote_weight
        + movie.popularity * popularity_weight
    )
