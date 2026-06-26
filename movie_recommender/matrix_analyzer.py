"""numpy 评分矩阵构建与分析函数。"""

import numpy as np


def _value(obj, key: str):
    return getattr(obj, key)


def build_rating_matrix(users, movies, ratings):
    """构建用户-电影评分矩阵，0 表示未评分。"""
    user_ids = [_value(user, 'user_id') for user in users]
    movie_ids = [_value(movie, 'movie_id') for movie in movies]
    user_to_idx = {user_id: idx for idx, user_id in enumerate(user_ids)}
    movie_to_idx = {movie_id: idx for idx, movie_id in enumerate(movie_ids)}

    matrix = np.zeros((len(user_ids), len(movie_ids)), dtype=float)

    if isinstance(ratings, dict):
        rating_items = [
            {'user_id': user_id, 'movie_id': movie_id, 'rating': rating}
            for user_id, movie_ratings in ratings.items()
            for movie_id, rating in movie_ratings.items()
        ]
    else:
        rating_items = ratings

    for rating in rating_items:
        user_idx = user_to_idx.get(rating['user_id'])
        movie_idx = movie_to_idx.get(rating['movie_id'])
        if user_idx is not None and movie_idx is not None:
            matrix[user_idx, movie_idx] = rating['rating']

    return matrix, user_ids, movie_ids


def build_index_maps(user_ids, movie_ids):
    """把 id 列表转成 {id: idx} 字典，让路由里 O(N) 的 .index() 变 O(1)。"""
    return (
        {uid: i for i, uid in enumerate(user_ids)},
        {mid: i for i, mid in enumerate(movie_ids)},
    )


def _average_nonzero(rating_matrix: np.ndarray, axis: int) -> np.ndarray:
    matrix = np.asarray(rating_matrix, dtype=float)
    counts = np.count_nonzero(matrix, axis=axis)
    sums = matrix.sum(axis=axis)
    return np.divide(
        sums,
        counts,
        out=np.zeros_like(sums, dtype=float),
        where=counts > 0,
    )


def analyze_movie_average_scores(rating_matrix: np.ndarray) -> np.ndarray:
    """忽略 0，计算每部电影平均评分。"""
    return _average_nonzero(rating_matrix, axis=0)


def analyze_user_average_scores(rating_matrix: np.ndarray) -> np.ndarray:
    """忽略 0，计算每个用户平均评分。"""
    return _average_nonzero(rating_matrix, axis=1)


def count_movie_ratings(rating_matrix: np.ndarray) -> np.ndarray:
    """统计每部电影评分次数。"""
    return np.count_nonzero(rating_matrix, axis=0)


def count_user_ratings(rating_matrix: np.ndarray) -> np.ndarray:
    """统计每个用户评分数量。"""
    return np.count_nonzero(rating_matrix, axis=1)


def compute_user_similarity_matrix(rating_matrix: np.ndarray) -> np.ndarray:
    """使用余弦相似度计算用户相似度矩阵。"""
    matrix = np.asarray(rating_matrix, dtype=float)
    if matrix.size == 0:
        return np.zeros((0, 0), dtype=float)

    dot_products = matrix @ matrix.T
    norms = np.linalg.norm(matrix, axis=1)
    denominators = np.outer(norms, norms)
    with np.errstate(divide='ignore', invalid='ignore'):
        similarity = np.divide(
            dot_products,
            denominators,
            out=np.zeros_like(dot_products, dtype=float),
            where=denominators > 0,
        )
    return similarity


def analyze_rating_matrix(rating_matrix: np.ndarray) -> dict:
    """汇总评分矩阵常用分析指标，便于 CLI/Web 展示。"""
    matrix = np.asarray(rating_matrix, dtype=float)
    rated_count = int(np.count_nonzero(matrix))
    total_cells = int(matrix.size)
    density = rated_count / total_cells if total_cells else 0.0
    nonzero_scores = matrix[matrix > 0]

    return {
        'movie_average_scores': analyze_movie_average_scores(matrix),
        'user_average_scores': analyze_user_average_scores(matrix),
        'movie_rating_counts': count_movie_ratings(matrix),
        'user_rating_counts': count_user_ratings(matrix),
        'user_similarity_matrix': compute_user_similarity_matrix(matrix),
        'rated_count': rated_count,
        'total_cells': total_cells,
        'density': density,
        'global_average': float(nonzero_scores.mean()) if nonzero_scores.size else 0.0,
    }
