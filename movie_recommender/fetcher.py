import json
import requests
import time
from pathlib import Path
from movie_recommender.models import Movie
from movie_recommender import cleaner


def fetch_movies_from_tmdb(bearer_token: str, page: int = 1, language: str = "zh-CN") -> list[dict]:
    """
    从 TMDB API 获取热门电影数据。
    如果 Bearer Token 不存在或请求失败，返回空列表。
    """
    if not bearer_token:
        return []
    url = "https://api.themoviedb.org/3/movie/top_rated"
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {"page": page, "language": language}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        movies = []
        for item in data.get('results', []):
            movie_id = item['id']
            title = cleaner.clean_title(item.get('title', ''))
            overview = cleaner.clean_overview(item.get('overview', ''))
            release_date = item.get('release_date', '')
            release_year = cleaner.extract_year(release_date)
            vote_average = cleaner.clean_rating(item.get('vote_average', 0.0))
            popularity = cleaner.clean_rating(item.get('popularity', 0.0))
            movies.append({
                'movie_id': movie_id,
                'title': title,
                'overview': overview,
                'release_year': release_year,
                'vote_average': vote_average,
                'popularity': popularity,
                'source': 'TMDB',
            })
        return movies
    except Exception as e:
        print(f"TMDB API 请求失败（第 {page} 页）: {e}")
        return []


def fetch_movie_details(bearer_token: str, movie_id: int) -> dict:
    """获取单部电影的详细信息（类型）。"""
    if not bearer_token:
        return {}
    base_url = "https://api.themoviedb.org/3"
    headers = {"Authorization": f"Bearer {bearer_token}"}
    try:
        resp = requests.get(f"{base_url}/movie/{movie_id}", headers=headers, timeout=15)
        resp.raise_for_status()
        details = resp.json()
        genres = [g['name'] for g in details.get('genres', [])]
        genres_str = '/'.join(genres) if genres else "未知"
        return {
            'genres_str': genres_str,
            'poster_path': details.get('poster_path'),
            'source': 'TMDB',
        }
    except Exception as e:
        print(f"获取电影详情失败（ID: {movie_id}）: {e}")
        return {}


def _fetch_movie_details_with_retry(bearer_token: str, movie_id: int, max_retries: int = 3) -> dict:
    """获取单部电影详情，失败时最多重试 max_retries 次。"""
    for attempt in range(max_retries):
        details = fetch_movie_details(bearer_token, movie_id)
        if details:
            return details
        if attempt < max_retries - 1:
            time.sleep(1)
    return {}


def fetch_all_movies(bearer_token: str, count: int = 250, max_retries: int = 3) -> list[Movie]:
    """获取最多 count 部 TMDB 电影，包含详情。"""
    movies = []
    page = 1
    consecutive_failures = 0
    while len(movies) < count and page <= 20:
        print(f"正在获取 TMDB Top Rated 第 {page} 页...")
        items = fetch_movies_from_tmdb(bearer_token, page=page)
        if not items:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                print(f"连续 {consecutive_failures} 页获取失败，终止爬取")
                break
            print(f"第 {page} 页获取失败，重试中 ({consecutive_failures}/3)...")
            time.sleep(2)
            continue
        consecutive_failures = 0
        for item in items:
            if len(movies) >= count:
                break
            movie_id = item['movie_id']
            details = _fetch_movie_details_with_retry(bearer_token, movie_id, max_retries=max_retries)
            time.sleep(0.2)
            movie = Movie(
                movie_id=movie_id,
                title=item['title'],
                overview=item['overview'],
                release_year=item['release_year'],
                genres=cleaner.parse_genres(details.get('genres_str', '')),
                vote_average=item['vote_average'],
                popularity=item['popularity'],
                poster_path=details.get('poster_path'),
                source=item.get('source', 'TMDB')
            )
            movies.append(movie)
            print(f"  + {movie.title} ({movie.vote_average}分)")
        page += 1
        time.sleep(1)
    return movies


def load_sample_movies() -> list[Movie]:
    """返回内置示例电影数据，保证没有 Bearer Token 时项目也能运行。"""
    sample_file = Path(__file__).parent.parent / "data" / "sample_movies.json"
    with open(sample_file, encoding="utf-8") as f:
        sample_data = json.load(f)
    movies = []
    for item in sample_data:
        movies.append(Movie(
            movie_id=item['movie_id'],
            title=item['title'],
            overview=item['overview'],
            release_year=item['release_year'],
            genres=item['genres'],
            vote_average=item['vote_average'],
            popularity=item['popularity'],
            poster_path=item.get('poster_path'),
            source=item.get('source', 'sample')
        ))
    return movies
