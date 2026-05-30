"""示例用户和评分初始化。"""


def seed_sample_users(db, sample_users, replace: bool = False) -> None:
    """创建或补齐示例用户评分，重复执行不会产生重复评分。"""
    users_by_name = {user.name: user for user in db.get_all_users()}

    for name, ratings in sample_users:
        user = users_by_name.get(name)
        if user is None:
            user_id = db.create_user(name)
            users_by_name[name] = next(
                u for u in db.get_all_users() if u.user_id == user_id
            )
            print(f"  创建用户: {name} (ID: {user_id})")
        else:
            user_id = user.user_id

        valid_movie_ids = {movie_id for movie_id, _ in ratings if db.movie_exists(movie_id)}
        if replace:
            for movie_id in set(db.get_user_ratings(user_id)) - valid_movie_ids:
                db.delete_rating(user_id, movie_id)

        for movie_id, rating in ratings:
            if db.movie_exists(movie_id):
                db.add_or_update_rating(user_id, movie_id, rating)
