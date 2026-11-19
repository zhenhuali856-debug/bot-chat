import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Optional, Set, Tuple
from fastapi import Depends, HTTPException, Request

TOKEN_TTL_SECONDS = 7 * 24 * 3600  # 7 天有效期
PBKDF2_ITERATIONS = 100_000

# 内存已登出 token 黑名单（记录 jti -> exp_ts，避免登出后继续复用）
_revoked_tokens: Dict[str, float] = {}


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """使用 PBKDF2-HMAC-SHA256 加盐哈希密码，禁止明文存储"""
    salt_hex = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_hex.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return dk.hex(), salt_hex


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """常量时间比对密码哈希"""
    computed_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, password_hash)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _get_signing_secret() -> str:
    env_secret = os.environ.get("AUTH_SECRET_KEY", "").strip()
    if env_secret:
        return env_secret
    from app.core.memory import memory_manager

    secret = memory_manager.get_system_setting("auth_secret_key", "")
    if not secret:
        secret = secrets.token_hex(32)
        memory_manager.set_system_setting("auth_secret_key", secret)
    return secret


def _cleanup_revoked():
    now = time.time()
    expired = [jti for jti, exp in _revoked_tokens.items() if exp < now]
    for jti in expired:
        _revoked_tokens.pop(jti, None)


def create_token(user_id: str, username: str, role: str) -> str:
    """签发带时效的 HMAC-SHA256 签名 Token"""
    now = int(time.time())
    payload = {
        "uid": user_id,
        "u": username,
        "r": role,
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
        "jti": secrets.token_hex(12),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    secret = _get_signing_secret().encode("utf-8")
    sig = hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{payload_b64}.{sig_b64}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """校验签名 Token 合法性、时效及是否已登出"""
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        secret = _get_signing_secret().encode("utf-8")
        expected_sig = hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None

        jti = payload.get("jti", "")
        if jti and jti in _revoked_tokens:
            return None

        return payload
    except Exception:
        return None


def revoke_token(token: str) -> None:
    """登出时将 Token 加入黑名单使其立即失效"""
    _cleanup_revoked()
    payload = verify_token(token)
    if payload and payload.get("jti"):
        _revoked_tokens[payload["jti"]] = float(payload.get("exp", time.time() + 3600))


def extract_bearer_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


def get_current_user(request: Request) -> Dict[str, Any]:
    """
    FastAPI 鉴权依赖：
    1. 若携带有效 Bearer Token，返回对应活跃用户；
    2. 若未携带 Token 且未开启多用户模式（单人免登录模式），自动以默认 admin 身份进入；
    3. 若 Token 无效/过期，或开启了多用户模式且未登录，返回 401。
    """
    from app.core.memory import memory_manager

    token = extract_bearer_token(request)
    if token:
        payload = verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="登录凭证无效或已过期，请重新登录")
        user = memory_manager.get_user_by_id(payload.get("uid", ""))
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在，请重新登录")
        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="该账号已被禁用，请联系管理员")
        return user

    # 未携带 token：检查是否开启多用户模式
    multi_user = memory_manager.is_multi_user_mode()
    if multi_user:
        raise HTTPException(status_code=401, detail="当前为多用户模式，请先登录")

    # 单人免登录模式：自动返回默认管理员账号
    default_admin = memory_manager.get_default_admin_user()
    if not default_admin:
        raise HTTPException(status_code=500, detail="系统默认管理员账号未初始化")
    return default_admin


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """管理员专属权限依赖"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="权限不足：仅管理员可执行此操作")
    return current_user

