from typing import Optional
import re


def clean_text(text: str) -> str:
    """通用文本清洗：去 HTML 标签、特殊空白和首尾空格。"""
    if text is None:
        return ""
    text = str(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;|&#160;', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def clean_title(title: str) -> str:
    """清洗电影标题，去掉多余空格和特殊符号。"""
    title = clean_text(title)
    title = re.sub(r'["\'/\\]+', '', title)
    return title


def extract_year(date_text: str) -> Optional[int]:
    """从上映日期字符串中提取年份。"""
    if not date_text:
        return None
    match = re.search(r'(19|20)\d{2}', date_text)
    if match:
        return int(match.group())
    return None


def clean_overview(text: str) -> str:
    """清洗电影简介，去除 HTML 标签、多余换行、连续空格。"""
    return clean_text(text)


def clean_rating(rating_text) -> float:
    """从评分字段中提取数字评分，无法提取时返回 0.0。"""
    if rating_text is None:
        return 0.0
    match = re.search(r'\d+(?:\.\d+)?', str(rating_text))
    if not match:
        return 0.0
    return float(match.group())


def parse_genres(genre_text: str) -> list[str]:
    """将类型字符串（如 'Action,Adventure,Sci-Fi' 或 '动作/科幻'）转为列表。"""
    if not genre_text:
        return []
    genres = re.split(r'[,/\\]+', genre_text)
    return [g.strip() for g in genres if g.strip()]


