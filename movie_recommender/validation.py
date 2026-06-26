"""用户输入校验 — web 端和 CLI 共用。"""
import re
from typing import Tuple

# 用户名校验：1-32 字符，允许中文/字母/数字/空格/常见符号，但禁止控制字符和纯空白。
_USERNAME_RE = re.compile(r'^[\w一-鿿 \-_.,!@#$%^&()+=\[\]{};:\'"<>?/\\|`~]{1,32}$', re.UNICODE)
USERNAME_MAX_LENGTH = 32


def normalize_and_validate_username(raw: str) -> Tuple[bool, str, str]:
    """把原始输入去前后空白、校验长度和字符集。

    Returns:
        (ok, normalized_name, error_message)
        成功时 error_message 为空字符串。
    """
    if raw is None:
        return False, '', '用户名不能为空'
    name = raw.strip()
    if not name:
        return False, '', '用户名不能为空'
    if len(name) > USERNAME_MAX_LENGTH:
        return False, name, f'用户名不能超过 {USERNAME_MAX_LENGTH} 个字符'
    if not _USERNAME_RE.match(name):
        return False, name, '用户名包含不支持的字符，请使用字母/数字/中文/常见符号'
    return True, name, ''


def find_user_by_name(db, name: str):
    """O(N) 查找用户 by name。CLI 用足够。"""
    for u in db.get_all_users():
        if u.name == name:
            return u
    return None
