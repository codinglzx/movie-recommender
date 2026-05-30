from flask import Flask, abort, render_template, request, redirect, url_for, session, send_from_directory
import os
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from movie_recommender.database import Database
from movie_recommender.recommender import Recommender
from movie_recommender import visualization
from config import TMDB_BEARER_TOKEN, SAMPLE_MOVIE_COUNT, SAMPLE_USERS
from movie_recommender import fetcher
from movie_recommender.seeder import seed_sample_users


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'movie-recommender-secret-key-change-me')
db = Database()
POSTER_DIR = Path(__file__).parent / 'data' / 'posters'


def _safe_filename(filename):
    """安全的文件名，防止路径遍历"""
    return re.sub(r'[^a-zA-Z0-9._-]', '', filename)


def _poster_exists(movie_id):
    return (POSTER_DIR / f"{movie_id}.jpg").exists()


def _file_version(path: Path) -> int:
    return int(path.stat().st_mtime) if path.exists() else 0


@app.context_processor
def inject_user():
    user_id = session.get('user_id')
    user_name = None
    if user_id:
        user = db.get_user(user_id)
        if user:
            user_name = user.name
    return dict(user_name=user_name, poster_exists=_poster_exists)


@app.route('/')
def index():
    users = db.get_all_users()
    movies = db.get_all_movies()
    ratings = db.get_all_ratings()
    return render_template('index.html', users=users, movie_count=len(movies), rating_count=len(ratings))


@app.route('/movies')
def movies():
    all_movies = db.get_all_movies()
    years = sorted(set(m.release_year for m in all_movies if m.release_year), reverse=True)
    user_ratings = {r['movie_id']: r['rating'] for r in db.get_all_ratings() if r['user_id'] == session.get('user_id')}
    all_genres = []
    for m in all_movies:
        for g in m.genres:
            if g not in all_genres:
                all_genres.append(g)
    return render_template('movies.html', movies=all_movies, years=years, user_ratings=user_ratings, all_genres=all_genres)


@app.route('/login/<int:user_id>')
def login(user_id):
    if db.get_user(user_id):
        session['user_id'] = user_id
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


@app.route('/recommend/<int:user_id>')
def recommend(user_id):
    user = db.get_user(user_id)
    if not user:
        return redirect(url_for('index'))

    session['user_id'] = user_id

    user_ratings = db.get_user_ratings(user_id)

    recommender = Recommender(db)

    genre_recs = recommender.recommend_by_genre(user_id, top_n=5)
    cf_recs = recommender.recommend_collaborative(user_id, top_n=5)

    return render_template('recommend.html',
                           genre_recs=genre_recs,
                           cf_recs=cf_recs,
                           user_id=user_id,
                           user_name=user.name,
                           user_ratings=user_ratings)


@app.route('/charts/<int:user_id>')
def charts(user_id):
    user = db.get_user(user_id)
    if not user:
        return redirect(url_for('index'))

    if session.get('user_id') != user_id:
        session['user_id'] = user_id

    Path("static/images").mkdir(parents=True, exist_ok=True)
    rating_chart_path = Path("static/images/rating_distribution.png")
    genre_chart_path = Path("static/images/genre_preference.png")
    visualization.plot_rating_distribution(db, output_path=str(rating_chart_path), user_id=user_id)
    visualization.plot_genre_preference(db, output_path=str(genre_chart_path), user_id=user_id)

    movies = db.get_all_movies()
    movie_map = {movie.movie_id: movie for movie in movies}

    analysis = Recommender(db).analyze_rating_matrix()
    users = db.get_all_users()
    user_name_map = {u.user_id: u.name for u in users}
    current_user_avg = 0.0
    current_user_count = 0
    similar_users = []
    if user_id in analysis['user_ids']:
        user_idx = analysis['user_ids'].index(user_id)
        current_user_avg = float(analysis['user_average_scores'][user_idx])
        current_user_count = int(analysis['user_rating_counts'][user_idx])
        similarities = analysis['user_similarity_matrix'][user_idx]
        for idx, similarity in enumerate(similarities):
            other_user_id = analysis['user_ids'][idx]
            if other_user_id != user_id and similarity > 0:
                similar_users.append({
                    'name': user_name_map.get(other_user_id, f'用户 {other_user_id}'),
                    'similarity': round(float(similarity), 3),
                })
        similar_users.sort(key=lambda item: item['similarity'], reverse=True)

    top_movies = []
    for idx, movie_id in enumerate(analysis['movie_ids']):
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
        'current_user_average': round(current_user_avg, 2),
        'current_user_count': current_user_count,
        'top_movies': top_movies[:5],
        'similar_users': similar_users[:5],
    }

    return render_template('charts.html',
                           user_id=user_id,
                           user_name=user.name,
                           matrix_summary=matrix_summary,
                           rating_chart_version=_file_version(rating_chart_path),
                           genre_chart_version=_file_version(genre_chart_path))


@app.route('/init')
def init_route():
    """Initialize database and import movie data."""
    existing = db.get_all_movies()
    if not existing:
        if TMDB_BEARER_TOKEN:
            movies = fetcher.fetch_all_movies(TMDB_BEARER_TOKEN, SAMPLE_MOVIE_COUNT)
            if not movies:
                movies = fetcher.load_sample_movies()
        else:
            movies = fetcher.load_sample_movies()
        db.insert_movies(movies)

    seed_sample_users(db, SAMPLE_USERS)

    return redirect(url_for('index'))


@app.route('/user/add', methods=['POST'])
def add_user():
    name = request.form.get('name', '').strip()
    if not name:
        return redirect(url_for('index'))
    try:
        db.create_user(name)
    except Exception as e:
        print(f"创建用户失败: {e}")
    return redirect(url_for('index'))


@app.route('/api/rate', methods=['POST'])
def api_rate():
    """API endpoint for rating movies from the modal popup."""
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


if __name__ == '__main__':
    app.run(debug=True)
