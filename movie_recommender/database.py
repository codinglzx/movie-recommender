import sqlite3
from pathlib import Path
from typing import Dict, Optional
from movie_recommender.models import Movie, User


class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / 'data' / 'movies.db'
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    def init_db(self) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS movies (
                    movie_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    overview TEXT,
                    release_year INTEGER,
                    genres TEXT,
                    vote_average REAL,
                    popularity REAL,
                    poster_path TEXT,
                    source TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ratings (
                    rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    movie_id INTEGER NOT NULL,
                    rating REAL NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY(movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
                    UNIQUE(user_id, movie_id)
                )
            ''')

    def insert_movie(self, movie: Movie) -> None:
        with self._connect() as conn:
            conn.execute('''
                INSERT INTO movies (movie_id, title, overview, release_year, genres, vote_average, popularity, poster_path, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(movie_id) DO UPDATE SET
                    title = excluded.title,
                    overview = excluded.overview,
                    release_year = excluded.release_year,
                    genres = excluded.genres,
                    vote_average = excluded.vote_average,
                    popularity = excluded.popularity,
                    poster_path = excluded.poster_path,
                    source = excluded.source
            ''', (movie.movie_id, movie.title, movie.overview, movie.release_year,
                  movie.genre_text(), movie.vote_average, movie.popularity,
                  movie.poster_path, movie.source))

    def insert_movies(self, movies: list[Movie]) -> None:
        for movie in movies:
            self.insert_movie(movie)

    def create_user(self, name: str) -> int:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (name) VALUES (?)', (name,))
            return cursor.lastrowid

    def add_or_update_rating(self, user_id: int, movie_id: int, rating: float) -> None:
        if not 1 <= rating <= 5:
            raise ValueError("评分范围必须是 1-5")
        if not self.movie_exists(movie_id):
            raise ValueError(f"电影 {movie_id} 不存在")
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
            if not cursor.fetchone():
                raise ValueError(f"用户 {user_id} 不存在")
            cursor.execute('''
                INSERT INTO ratings (user_id, movie_id, rating)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, movie_id) DO UPDATE SET
                    rating = excluded.rating
            ''', (user_id, movie_id, rating))

    def delete_rating(self, user_id: int, movie_id: int) -> None:
        with self._connect() as conn:
            conn.execute('DELETE FROM ratings WHERE user_id = ? AND movie_id = ?', (user_id, movie_id))

    def delete_user(self, user_id: int) -> None:
        """删除用户（ratings 通过 ON DELETE CASCADE 自动清掉）。"""
        with self._connect() as conn:
            conn.execute('DELETE FROM users WHERE user_id = ?', (user_id,))

    def get_all_movies(self) -> list[Movie]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT movie_id, title, overview, release_year, genres, vote_average, popularity, poster_path, source
                FROM movies
                ORDER BY vote_average DESC, popularity DESC, release_year DESC, title ASC
            ''')
            rows = cursor.fetchall()
        movies = []
        for row in rows:
            genres_str = row[4] or ''
            genres = [g.strip() for g in genres_str.split(',') if g.strip()]
            movies.append(Movie(
                movie_id=row[0], title=row[1], overview=row[2] or '',
                release_year=row[3], genres=genres,
                vote_average=row[5] or 0.0, popularity=row[6] or 0.0,
                poster_path=row[7], source=row[8] or 'TMDB'
            ))
        return movies

    def get_user_ratings(self, user_id: int) -> Dict[int, float]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT movie_id, rating FROM ratings WHERE user_id = ? ORDER BY movie_id', (user_id,))
            rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}

    def get_all_ratings(self) -> list[dict]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, movie_id, rating FROM ratings ORDER BY user_id, movie_id')
            rows = cursor.fetchall()
        return [{'user_id': r[0], 'movie_id': r[1], 'rating': r[2]} for r in rows]

    def get_all_user_ratings(self) -> Dict[int, Dict[int, float]]:
        """返回嵌套字典：{user_id: {movie_id: rating}}。"""
        nested_ratings: Dict[int, Dict[int, float]] = {}
        for rating in self.get_all_ratings():
            nested_ratings.setdefault(rating['user_id'], {})[rating['movie_id']] = rating['rating']
        return nested_ratings

    def get_all_users(self) -> list[User]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, name FROM users ORDER BY user_id')
            rows = cursor.fetchall()
        ratings = self.get_all_user_ratings()
        return [User(user_id=r[0], name=r[1], ratings=ratings.get(r[0], {})) for r in rows]

    def get_user(self, user_id: int) -> Optional[User]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, name FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
        if row is None:
            return None
        return User(user_id=row[0], name=row[1], ratings=self.get_user_ratings(row[0]))

    def movie_exists(self, movie_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM movies WHERE movie_id = ?', (movie_id,))
            return cursor.fetchone() is not None

    def count_ratings(self) -> int:
        """O(1) 评分数，避免把整张 ratings 表拉到内存。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM ratings')
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def count_movies(self) -> int:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM movies')
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def count_users(self) -> int:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def count_users_with_ratings(self) -> int:
        """至少有 1 个评分的用户数 — 比 build_rating_matrix 便宜得多。"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM ratings')
            row = cursor.fetchone()
            return int(row[0]) if row else 0
