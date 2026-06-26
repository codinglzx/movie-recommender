"""示例用户和评分初始化。"""


def seed_sample_users(db, sample_users, replace: bool = False) -> None:
    """创建或补齐示例用户评分，重复执行不会产生重复评分。

    Args:
        replace: True 时执行"完全重置"——
            1. 删除所有不在 sample_users 里的用户（其评分通过 FK CASCADE 一并清掉）
            2. 对每个 sample 用户，删除不在新列表里的旧评分
            3. 写入新评分
    """
    sample_names = {name for name, _ in sample_users}

    if replace:
        # 第一步：清掉非 sample 用户
        for user in db.get_all_users():
            if user.name not in sample_names:
                db.delete_user(user.user_id)
                print(f"  移除非示例用户: {user.name}")

    users_by_name = {user.name: user for user in db.get_all_users()}

    for name, ratings in sample_users:
        user = users_by_name.get(name)
        if user is None:
            user_id = db.create_user(name)
            user = db.get_user(user_id)
            users_by_name[name] = user
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
