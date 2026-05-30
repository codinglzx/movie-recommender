import os

TMDB_BEARER_TOKEN = os.environ.get("TMDB_BEARER_TOKEN", "")
SAMPLE_MOVIE_COUNT = 250

SAMPLE_USERS = [
    ("Alice", [(155, 4), (27205, 5), (129, 4), (157336, 5), (19995, 4)]),
    ("Bob",   [(238, 5), (680, 4), (155, 5), (120, 4), (603, 4)]),
    ("Cindy", [(129, 5), (372058, 5), (324857, 4), (496243, 4), (603, 4)]),
]
