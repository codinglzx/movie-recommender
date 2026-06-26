import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = [
    'AR PL UMing CN', 'Droid Sans Fallback', 'WenQuanYi Micro Hei',
    'SimHei', 'Microsoft YaHei', 'DejaVu Sans'
]
plt.rcParams['axes.unicode_minus'] = False

FIG_BG = '#111827'
AX_BG = '#16213e'
TEXT = '#e5e7eb'
MUTED = '#9ca3af'
GRID = '#374151'
GOLD = '#c8a84e'
AMBER = '#d4895a'


def _default_path(filename: str) -> Path:
    return Path(__file__).parent.parent / "static" / "images" / filename


def plot_rating_distribution(db, output_path: str = None, user_id: int = None) -> None:
    """生成用户评分分布图。"""
    if output_path is None:
        output_path = str(_default_path("rating_distribution.png"))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if user_id is None:
        ratings = db.get_all_ratings()
        title = '用户评分分布'
    else:
        ratings = [
            {'movie_id': movie_id, 'rating': rating}
            for movie_id, rating in db.get_user_ratings(user_id).items()
        ]
        title = f'用户 {user_id} 评分分布'

    if not ratings:
        _generate_empty_chart("暂无评分数据", output_path)
        return

    rating_values = [r['rating'] for r in ratings]
    fig, ax = plt.subplots(figsize=(12, 7), facecolor=FIG_BG)
    ax.set_facecolor(AX_BG)
    ax.hist(rating_values, bins=5, range=(1, 5), edgecolor='#111827', alpha=0.9, color='#e94560')
    ax.set_title(title, fontsize=20, pad=15, color=TEXT)
    ax.set_xlabel('评分', fontsize=16, color=MUTED)
    ax.set_ylabel('数量', fontsize=16, color=MUTED)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.tick_params(axis='both', labelsize=14, colors=MUTED)
    ax.grid(axis='y', alpha=0.65, linestyle='--', color=GRID)
    for spine in ax.spines.values():
        spine.set_color('#263247')
    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_genre_preference(db, output_path: str = None, user_id: int = None) -> None:
    """生成用户类型偏好图；未传用户时生成全库类型分布图。"""
    if output_path is None:
        output_path = str(_default_path("genre_preference.png"))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    movies = db.get_all_movies()
    if not movies:
        _generate_empty_chart("暂无电影数据", output_path)
        return

    movie_map = {movie.movie_id: movie for movie in movies}
    genre_counts = {}

    if user_id is None:
        for movie in movies:
            for genre in movie.genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        title = '电影类型分布'
        ylabel = '数量'
    else:
        user_ratings = db.get_user_ratings(user_id)
        for movie_id, rating in user_ratings.items():
            movie = movie_map.get(movie_id)
            if not movie:
                continue
            for genre in movie.genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + rating
        title = f'用户 {user_id} 类型偏好'
        ylabel = '偏好得分'

    if not genre_counts:
        _generate_empty_chart("暂无类型数据", output_path)
        return

    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    genres = [g[0] for g in sorted_genres[:12]]
    counts = [g[1] for g in sorted_genres[:12]]

    fig, ax = plt.subplots(figsize=(14, 7), facecolor=FIG_BG)
    ax.set_facecolor(AX_BG)
    bars = ax.bar(genres, counts, alpha=0.9, color='#00d4ff')
    ax.set_title(title, fontsize=20, pad=15, color=TEXT)
    ax.set_xlabel('类型', fontsize=16, color=MUTED)
    ax.set_ylabel(ylabel, fontsize=16, color=MUTED)
    ax.tick_params(axis='x', labelsize=13, rotation=45, colors=MUTED)
    ax.tick_params(axis='y', labelsize=13, colors=MUTED)
    ax.grid(axis='y', alpha=0.5, linestyle='--', color=GRID)
    for spine in ax.spines.values():
        spine.set_color('#263247')
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.3,
                f'{bar.get_height():.1f}', ha='center', va='bottom', fontsize=12, color=TEXT)
    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)


def _generate_empty_chart(message: str, output_path: str) -> None:
    """生成空图表提示。"""
    fig = plt.figure(figsize=(10, 5), facecolor=FIG_BG)
    plt.text(0.5, 0.5, message, ha='center', va='center', fontsize=18, color=TEXT)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
