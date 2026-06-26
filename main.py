#!/usr/bin/env python3
"""Movie RecommenderEngine 命令行工具

用法:
    python3 main.py init                # 从 TMDB API 初始化数据库
    python3 main.py sample            # 使用内置示例数据初始化
    python3 main.py posters           # 下载电影海报
    python3 main.py add-user <name>   # 添加用户
    python3 main.py rate <user> <movie_id> <rating>  # 给电影评分
    python3 main.py recommend <user>   # 获取推荐
    python3 main.py charts <user>      # 生成图表
    python3 main.py analyze [user]     # numpy 评分矩阵分析
"""

import argparse
import sys
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from movie_recommender.database import Database
from movie_recommender import fetcher
from movie_recommender.seeder import seed_sample_users
from movie_recommender import visualization
from movie_recommender.recommender import RecommenderEngine
from movie_recommender.validation import normalize_and_validate_username, find_user_by_name
from config import TMDB_BEARER_TOKEN, SAMPLE_MOVIE_COUNT, SAMPLE_USERS


def cmd_init():
    """从 TMDB API 获取电影数据初始化数据库（增量：已有的不重复，没有的补上）。"""
    if not TMDB_BEARER_TOKEN:
        print("错误: 请先配置 TMDB_BEARER_TOKEN 环境变量")
        print("提示: 如果想使用示例数据，请运行: make sample")
        return

    print("正在初始化数据库...")
    db = Database()

    existing_ids = {m.movie_id for m in db.get_all_movies()}
    print(f"数据库中已有 {len(existing_ids)} 部电影")

    print(f"正在从 TMDB API 获取电影数据（Token: {TMDB_BEARER_TOKEN[:8]}...）...")
    movies = fetcher.fetch_all_movies(TMDB_BEARER_TOKEN, count=SAMPLE_MOVIE_COUNT)
    if not movies:
        print("TMDB 数据获取失败，改用内置示例数据继续初始化。")
        movies = fetcher.load_sample_movies()

    movies_to_add = [m for m in movies if m.movie_id not in existing_ids]
    if movies:
        print(f"正在导入或更新 {len(movies)} 部电影，其中新增 {len(movies_to_add)} 部...")
        db.insert_movies(movies)
        print("电影数据导入或更新完成。")
    else:
        print("本次没有获取到电影，跳过导入。")

    print("创建或补齐示例用户和评分...")
    seed_sample_users(db, SAMPLE_USERS, replace=True)
    print("示例用户和评分已就绪。")

    print("正在生成可视化图表...")
    visualization.plot_rating_distribution(db)
    visualization.plot_genre_preference(db)
    print("初始化完成！")


def cmd_sample():
    """使用内置示例数据初始化数据库（增量：已有的不重复，没有的补上）。"""
    print("正在使用内置示例数据初始化数据库...")
    db = Database()

    existing_ids = {m.movie_id for m in db.get_all_movies()}
    sample_movies = fetcher.load_sample_movies()
    movies_to_add = []
    for m in sample_movies:
        if m.movie_id not in existing_ids:
            movies_to_add.append(m)

    print(f"正在导入或更新 {len(sample_movies)} 部示例电影，其中新增 {len(movies_to_add)} 部...")
    db.insert_movies(sample_movies)
    print("电影数据导入或更新完成。")

    print("创建或补齐示例用户和评分...")
    seed_sample_users(db, SAMPLE_USERS, replace=True)
    print("示例用户和评分已就绪。")

    print("正在生成可视化图表...")
    visualization.plot_rating_distribution(db)
    visualization.plot_genre_preference(db)
    print("初始化完成！")


def cmd_download_posters():
    """下载电影海报。"""
    if not TMDB_BEARER_TOKEN:
        print("错误: TMDB_BEARER_TOKEN 未设置，无法下载海报")
        print("提示: 请先配置 TMDB_BEARER_TOKEN 环境变量")
        return

    db = Database()
    movies = db.get_all_movies()
    if not movies:
        print("数据库为空，请先运行: python3 main.py init")
        return

    POSTERS_DIR = Path(__file__).parent / "data" / "posters"
    POSTERS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"共 {len(movies)} 部电影，开始下载海报...")

    headers = {"Authorization": f"Bearer {TMDB_BEARER_TOKEN}"}
    TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
    success_count = 0
    skip_count = 0

    for movie in movies:
        local_path = POSTERS_DIR / f"{movie.movie_id}.jpg"
        if local_path.exists():
            skip_count += 1
            continue

        try:
            resp = requests.get(
                f"https://api.themoviedb.org/3/movie/{movie.movie_id}",
                headers=headers,
                timeout=15
            )
            resp.raise_for_status()
            details = resp.json()
            poster_path = details.get("poster_path")

            if poster_path:
                img_resp = requests.get(
                    f"{TMDB_IMAGE_BASE}{poster_path}",
                    timeout=30
                )
                img_resp.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(img_resp.content)
                print(f"  ✓ {details.get('title', movie.movie_id)}")
                success_count += 1
            else:
                print(f"  ✗ 无海报: {movie.movie_id}")

        except Exception as e:
            print(f"  ✗ 失败 ({movie.movie_id}): {e}")

    print(f"\n完成! 成功下载 {success_count} 张，跳过 {skip_count} 张已有海报")


def cmd_add_user(name: str):
    """添加新用户。"""
    ok, normalized, err = normalize_and_validate_username(name)
    if not ok:
        print(f"错误: {err}")
        return
    db = Database()
    if find_user_by_name(db, normalized):
        print(f"错误: 用户名 \"{normalized}\" 已被占用")
        return
    try:
        user_id = db.create_user(normalized)
        print(f"用户创建成功: {normalized} (ID: {user_id})")
    except Exception as e:
        print(f"创建用户失败: {e}")


def cmd_rate(user_name: str, movie_id: int, rating: float, create: bool = False):
    """给电影评分。"""
    if not 1 <= rating <= 5:
        print(f"错误: 评分必须在 1-5 之间，当前值: {rating}")
        return
    db = Database()
    user = find_user_by_name(db, user_name)
    if not user:
        if not create:
            # 默认拒绝拼错：宁可让用户重输，也不要留垃圾用户
            print(f"错误: 用户 \"{user_name}\" 不存在。")
            print(f"提示: 如需自动创建，请加 --create：python3 main.py rate {user_name} {movie_id} {rating} --create")
            print(f"      或先运行: python3 main.py add-user {user_name}")
            return
        ok, normalized, err = normalize_and_validate_username(user_name)
        if not ok:
            print(f"错误: {err}")
            return
        user_id = db.create_user(normalized)
        print(f"创建新用户: {normalized} (ID: {user_id})")
    else:
        user_id = user.user_id
    try:
        db.add_or_update_rating(user_id, movie_id, rating)
        print(f"评分成功: {user_name} 对电影 {movie_id} 评 {rating} 分")
    except ValueError as e:
        print(f"评分失败 (数据错误): {e}")
    except Exception as e:
        print(f"评分失败 (系统错误): {type(e).__name__}: {e}")


def cmd_recommend(user_name: str):
    """获取推荐。"""
    db = Database()
    user = find_user_by_name(db, user_name)
    if not user:
        print(f"用户 {user_name} 不存在")
        return
    user_id = user.user_id

    recommender = RecommenderEngine(db)

    print(f"\n=== 基于类型偏好的推荐 (用户: {user_name}) ===")
    genre_recs = recommender.recommend_by_genre(user_id, top_n=5)
    for r in genre_recs:
        print(f"  [{r['method']}] {r['movie'].title} (score: {r['score']})")

    print(f"\n=== 基于协同过滤的推荐 (用户: {user_name}) ===")
    cf_recs = recommender.recommend_collaborative(user_id, top_n=5)
    for r in cf_recs:
        print(f"  [{r['method']}] {r['movie'].title} (score: {r['score']})")


def cmd_charts(user_name: str):
    """生成可视化图表。"""
    db = Database()
    user = find_user_by_name(db, user_name)
    if not user:
        print(f"用户 {user_name} 不存在")
        return
    user_id = user.user_id

    visualization.plot_rating_distribution(db, user_id=user_id)
    visualization.plot_genre_preference(db, user_id=user_id)
    print("图表已生成")


def cmd_analyze(user_name: str = None):
    """使用 numpy 分析评分矩阵。"""
    db = Database()
    recommender = RecommenderEngine(db)
    analysis = recommender.analyze_rating_matrix()
    users = db.get_all_users()
    movies = {m.movie_id: m for m in db.get_all_movies()}

    print("\n=== numpy 评分矩阵分析 ===")
    print(f"矩阵维度: {len(analysis['user_ids'])} 用户 x {len(analysis['movie_ids'])} 电影")
    print(f"已评分单元: {analysis['rated_count']} / {analysis['total_cells']}")
    print(f"矩阵密度: {analysis['density'] * 100:.2f}%")
    print(f"全局平均评分: {analysis['global_average']:.2f}")

    movie_id_to_idx = analysis['movie_id_to_idx']
    top_movies = []
    for movie_id, idx in movie_id_to_idx.items():
        count = int(analysis['movie_rating_counts'][idx])
        if count:
            top_movies.append((
                float(analysis['movie_average_scores'][idx]),
                count,
                movies[movie_id].title if movie_id in movies else str(movie_id),
            ))
    top_movies.sort(reverse=True)

    print("\n评分最高电影 Top 5:")
    for average, count, title in top_movies[:5]:
        print(f"  {title}: 平均 {average:.2f}，评分次数 {count}")

    if user_name:
        user = find_user_by_name(db, user_name)
        if not user:
            print(f"\n用户 {user_name} 不存在")
            return
        user_id = user.user_id
        user_id_to_idx = analysis['user_id_to_idx']
        if user_id not in user_id_to_idx:
            print(f"\n用户 {user_name} 暂无评分矩阵数据")
            return
        user_idx = user_id_to_idx[user_id]
        user_avg = analysis['user_average_scores'][user_idx]
        user_count = analysis['user_rating_counts'][user_idx]
        print(f"\n用户 {user_name}: 平均评分 {user_avg:.2f}，评分数量 {int(user_count)}")

        name_by_id = {u.user_id: u.name for u in users}
        similarities = []
        for idx, similarity in enumerate(analysis['user_similarity_matrix'][user_idx]):
            other_id = analysis['user_ids'][idx]
            if other_id != user_id and similarity > 0:
                similarities.append((float(similarity), name_by_id.get(other_id, str(other_id))))
        similarities.sort(reverse=True)
        print("相似用户:")
        for similarity, name in similarities[:5]:
            print(f"  {name}: {similarity:.3f}")


def main():
    parser = argparse.ArgumentParser(description="Movie RecommenderEngine CLI")
    subparsers = parser.add_subparsers(dest='command')

    p_init = subparsers.add_parser('init', help='从 TMDB API 初始化数据库')
    p_sample = subparsers.add_parser('sample', help='使用内置示例数据初始化')
    p_posters = subparsers.add_parser('posters', help='下载电影海报')
    p_add = subparsers.add_parser('add-user', help='添加用户')
    p_add.add_argument('name', help='用户名')
    p_rate = subparsers.add_parser('rate', help='给电影评分')
    p_rate.add_argument('user')
    p_rate.add_argument('movie_id', type=int)
    p_rate.add_argument('rating', type=float)
    p_rate.add_argument('--create', action='store_true', help='用户不存在时自动创建（默认拒绝拼错，避免垃圾用户）')
    p_rec = subparsers.add_parser('recommend', help='获取推荐')
    p_rec.add_argument('user', help='用户名')
    p_charts = subparsers.add_parser('charts', help='生成图表')
    p_charts.add_argument('user', help='用户名')
    p_analyze = subparsers.add_parser('analyze', help='numpy 评分矩阵分析')
    p_analyze.add_argument('user', nargs='?', help='可选用户名')

    args = parser.parse_args()

    if args.command == 'init':
        cmd_init()
    elif args.command == 'sample':
        cmd_sample()
    elif args.command == 'posters':
        cmd_download_posters()
    elif args.command == 'add-user':
        cmd_add_user(args.name)
    elif args.command == 'rate':
        cmd_rate(args.user, args.movie_id, args.rating, create=args.create)
    elif args.command == 'recommend':
        cmd_recommend(args.user)
    elif args.command == 'charts':
        cmd_charts(args.user)
    elif args.command == 'analyze':
        cmd_analyze(args.user)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
