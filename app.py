from flask import Flask, abort, render_template, request, redirect, url_for, session, send_from_directory, flash
import os
import re
import secrets
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from movie_recommender.database import Database
from movie_recommender.recommender import RecommenderEngine
from movie_recommender import visualization
from movie_recommender.validation import normalize_and_validate_username
from config import TMDB_BEARER_TOKEN, SAMPLE_MOVIE_COUNT, SAMPLE_USERS
from movie_recommender import fetcher
from movie_recommender.seeder import seed_sample_users


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'movie-recommender-secret-key-change-me')
db = Database()
POSTER_DIR = Path(__file__).parent / 'data' / 'posters'
IMAGES_DIR = Path(__file__).parent / "static" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(filename):
    """安全的文件名，防止路径遍历"""
    return re.sub(r'[^a-zA-Z0-9._-]', '', filename)


def _poster_exists(movie_id):
    return (POSTER_DIR / f"{movie_id}.jpg").exists()


# ========== CSRF 防护 ==========
def _get_or_create_csrf_token() -> str:
    """每个会话一个 CSRF token，存在 session 里。"""
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


def _verify_csrf_token() -> bool:
    """校验 POST/PUT/DELETE 请求的 CSRF token。GET/HEAD/OPTIONS 放行。"""
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return True
    token_session = session.get('_csrf_token', '')
    token_form = request.form.get('_csrf_token', '')
    token_header = request.headers.get('X-CSRF-Token', '')
    token = token_form or token_header
    if not token_session or not token:
        return False
    return secrets.compare_digest(token_session, token)


@app.context_processor
def inject_globals():
    user_id = session.get('user_id')
    user_name = None
    if user_id:
        user = db.get_user(user_id)
        if user:
            user_name = user.name
    return dict(
        user_name=user_name,
        poster_exists=_poster_exists,
        csrf_token_value=_get_or_create_csrf_token(),
    )


@app.route('/')
def index():
    users = db.get_all_users()
    # 用 O(1) COUNT 替代把整张表拉回内存
    return render_template(
        'index.html',
        users=users,
        movie_count=db.count_movies(),
        rating_count=db.count_ratings(),
    )


@app.route('/movies')
def movies():
    all_movies = db.get_all_movies()
    years = sorted({m.release_year for m in all_movies if m.release_year}, reverse=True)
    current_user_id = session.get('user_id')
    user_ratings = db.get_user_ratings(current_user_id) if current_user_id else {}
    all_genres = list(dict.fromkeys(g for m in all_movies for g in m.genres))
    return render_template('movies.html', movies=all_movies, years=years, user_ratings=user_ratings, all_genres=all_genres)


@app.route('/login/<int:user_id>', methods=['POST'])
def login(user_id):
    """切换登录身份(POST + CSRF,防止跨站 <img src=/login/N> 静默劫持会话)。"""
    if not _verify_csrf_token():
        flash('会话已过期，请刷新页面后重试', 'error')
        return redirect(url_for('index'))
    user = db.get_user(user_id)
    if user:
        session['user_id'] = user_id
        flash(f'已登录为 {user.name}', 'success')
    else:
        flash('该用户不存在', 'error')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    user = db.get_user(session['user_id']) if session.get('user_id') else None
    session.pop('user_id', None)
    if user:
        flash(f'已退出 {user.name}', 'info')
    return redirect(url_for('index'))


@app.route('/recommend/<int:user_id>')
def recommend(user_id):
    """查看某个用户的推荐(只读视图,不写 session — 切换身份请走 POST /login)。"""
    user = db.get_user(user_id)
    if not user:
        flash('该用户不存在', 'error')
        return redirect(url_for('index'))

    user_ratings = db.get_user_ratings(user_id)

    recommender = RecommenderEngine(db)
    genre_status = recommender.genre_recommendation_status(user_id)
    cf_status = recommender.collaborative_recommendation_status(user_id)
    genre_recs = recommender.recommend_by_genre(user_id, top_n=5) if genre_status['available'] else []
    cf_recs = recommender.recommend_collaborative(user_id, top_n=5) if cf_status['available'] else []

    return render_template('recommend.html',
                           genre_recs=genre_recs,
                           cf_recs=cf_recs,
                           genre_status=genre_status,
                           cf_status=cf_status,
                           user_id=user_id,
                           user_name=user.name,
                           user_ratings=user_ratings)


@app.route('/charts/<int:user_id>')
def charts(user_id):
    """查看某个用户的图表(只读视图,不写 session)。"""
    user = db.get_user(user_id)
    if not user:
        flash('该用户不存在', 'error')
        return redirect(url_for('index'))

    # 每个用户拥有独立的图表文件，避免串图，并免去额外缓存版本号
    rating_chart_path = IMAGES_DIR / f"rating_distribution_{user_id}.png"
    genre_chart_path = IMAGES_DIR / f"genre_preference_{user_id}.png"

    if not rating_chart_path.exists():
        visualization.plot_rating_distribution(db, output_path=str(rating_chart_path), user_id=user_id)
    if not genre_chart_path.exists():
        visualization.plot_genre_preference(db, output_path=str(genre_chart_path), user_id=user_id)

    # 一次性取出所有用户和电影，在内存里建 O(1) 查找表
    movies = db.get_all_movies()
    movie_map = {movie.movie_id: movie for movie in movies}
    users = db.get_all_users()
    user_name_map = {u.user_id: u.name for u in users}

    analysis = RecommenderEngine(db).analyze_rating_matrix()
    user_id_to_idx = analysis['user_id_to_idx']

    # O(1) 查当前用户
    user_idx = user_id_to_idx.get(user_id)
    current_user_count = 0
    current_user_avg = 0.0
    similar_users = []
    if user_idx is not None:
        current_user_avg = float(analysis['user_average_scores'][user_idx])
        current_user_count = int(analysis['user_rating_counts'][user_idx])
        similarities = analysis['user_similarity_matrix'][user_idx]
        # similarity > 0：剔除完全不相似（评分向量正交）的用户
        for idx, similarity in enumerate(similarities):
            other_user_id = analysis['user_ids'][idx]
            if other_user_id != user_id and similarity > 0:
                similar_users.append({
                    'name': user_name_map.get(other_user_id, f'用户 {other_user_id}'),
                    'similarity': round(float(similarity), 3),
                })
        similar_users.sort(key=lambda item: item['similarity'], reverse=True)

    # O(1) 查电影
    movie_id_to_idx = analysis['movie_id_to_idx']
    top_movies = []
    for movie_id, idx in movie_id_to_idx.items():
        count = int(analysis['movie_rating_counts'][idx])
        if count == 0:
            continue
        movie = movie_map.get(movie_id)
        top_movies.append({
            'title': movie.title if movie else f'电影 {movie_id}',
            'average': round(float(analysis['movie_average_scores'][idx]), 2),
            'count': count,
        })
    top_movies.sort(key=lambda item: (item['average'], item['count']), reverse=True)

    matrix_summary = {
        'user_count': len(analysis['user_ids']),
        'movie_count': len(analysis['movie_ids']),
        'rated_count': analysis['rated_count'],
        'density_percent': round(analysis['density'] * 100, 2),
        'global_average': round(analysis['global_average'], 2),
        'current_user_average': round(current_user_avg, 2) if current_user_count else None,
        'current_user_count': current_user_count,
        'top_movies': top_movies[:5],
        'similar_users': similar_users[:5],
    }

    return render_template('charts.html',
                           user_id=user_id,
                           user_name=user.name,
                           matrix_summary=matrix_summary,
                           rating_chart_filename=f"rating_distribution_{user_id}.png",
                           genre_chart_filename=f"genre_preference_{user_id}.png")


@app.route('/init', methods=['POST'])
def init_route():
    """初始化数据库和导入电影数据（POST + CSRF，防止 CSRF 攻击）。"""
    if not _verify_csrf_token():
        flash('无效的请求令牌，请刷新页面后重试', 'error')
        return redirect(url_for('index'))
    existing = db.get_all_movies()
    if not existing:
        if TMDB_BEARER_TOKEN:
            movies = fetcher.fetch_all_movies(TMDB_BEARER_TOKEN, SAMPLE_MOVIE_COUNT)
            if not movies:
                movies = fetcher.load_sample_movies()
        else:
            movies = fetcher.load_sample_movies()
        db.insert_movies(movies)
        flash(f'已加载 {len(movies)} 部电影', 'success')

    # 与 main.py init 行为一致：replace=True 清理孤儿评分，让 /init 真正"重置"
    seed_sample_users(db, SAMPLE_USERS, replace=True)
    sample_user_ids = {u.user_id for u in db.get_all_users()}

    # 清理掉非 sample 用户的图表缓存，避免孤儿文件
    for png in IMAGES_DIR.glob('*.png'):
        try:
            user_id = int(png.stem.rsplit('_', 1)[-1])
        except (ValueError, IndexError):
            continue
        if user_id not in sample_user_ids:
            try:
                png.unlink()
            except OSError:
                pass

    flash('示例用户和评分已就绪', 'success')
    return redirect(url_for('index'))


@app.route('/user/add', methods=['POST'])
def add_user():
    """创建新用户并自动登录，跳转到首页。"""
    if not _verify_csrf_token():
        flash('会话已过期，请刷新页面后重试', 'error')
        return redirect(url_for('index'))

    ok, name, error = normalize_and_validate_username(request.form.get('name', ''))
    if not ok:
        flash(error, 'error')
        return redirect(url_for('index'))

    try:
        new_id = db.create_user(name)
    except sqlite3.IntegrityError:
        flash(f'用户名 "{name}" 已被占用，请换一个', 'error')
    except Exception as e:
        # 兜底:SQLite 其他异常(磁盘满、权限等)
        flash(f'创建用户失败：{e}', 'error')
    else:
        # 仅当 create_user 成功时设置 session
        session['user_id'] = new_id
        flash(f'欢迎，{name}！已为你自动登录', 'success')
    return redirect(url_for('index'))


def _invalidate_user_charts(user_id: int) -> None:
    """评分变更后清除该用户的图表缓存，下一次访问 /charts 会重新生成。"""
    for filename in (f"rating_distribution_{user_id}.png", f"genre_preference_{user_id}.png"):
        target = IMAGES_DIR / filename
        try:
            if target.exists():
                target.unlink()
        except OSError as e:
            print(f"清理图表缓存失败 ({filename}): {e}")


@app.route('/api/rate', methods=['POST'])
def api_rate():
    """API endpoint for rating movies from the modal popup."""
    if not _verify_csrf_token():
        return {'error': '会话已过期，请刷新页面'}, 403

    user_id = session.get('user_id')
    if not user_id:
        return {'error': '请先登录'}, 401

    movie_id = request.form.get('movie_id', type=int)
    rating = request.form.get('rating', type=float)

    if movie_id is None or rating is None:
        return {'error': '缺少参数'}, 400

    if not 1 <= rating <= 5:
        return {'error': '评分必须是1-5'}, 400

    try:
        db.add_or_update_rating(user_id, movie_id, rating)
        _invalidate_user_charts(user_id)
        return {'success': True, 'rating': rating}
    except ValueError as e:
        return {'error': str(e)}, 400


@app.route('/posters/<filename>')
def serve_poster(filename):
    safe_name = _safe_filename(filename)
    poster_path = POSTER_DIR / safe_name
    if not safe_name.endswith('.jpg') or not poster_path.exists():
        abort(404)
    return send_from_directory(str(POSTER_DIR), safe_name)


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(debug=True)
