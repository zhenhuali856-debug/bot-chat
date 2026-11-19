from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.core.auth import (
    create_token,
    extract_bearer_token,
    get_current_user,
    require_admin,
    revoke_token,
    verify_password,
)
from app.core.memory import memory_manager
from app.models import (
    AuthModeRequest,
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    UpdateUserRequest,
)

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/login")
async def login_endpoint(req: LoginRequest):
    """用户登录：校验加盐哈希密码并签发有时效的签名 Token"""
    username = (req.username or "").strip()
    if not username or not req.password:
        raise HTTPException(status_code=400, detail="请输入用户名和密码")

    user_secret = memory_manager.get_user_by_username(username, include_secret=True)
    if not user_secret:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user_secret.get("is_active", True):
        raise HTTPException(status_code=403, detail="该账号已被禁用，请联系管理员")

    if not verify_password(req.password, user_secret["password_hash"], user_secret["salt"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    memory_manager.update_user_last_login(user_secret["id"])
    token = create_token(user_secret["id"], user_secret["username"], user_secret["role"])
    safe_user = memory_manager.get_user_by_id(user_secret["id"])
    return {
        "token": token,
        "user": safe_user,
        "multi_user_mode": memory_manager.is_multi_user_mode(),
    }


@router.post("/auth/logout")
async def logout_endpoint(request: Request):
    """退出登录：使当前 Token 立即失效"""
    token = extract_bearer_token(request)
    if token:
        revoke_token(token)
    return {"success": True, "message": "已退出登录"}


@router.get("/auth/me")
async def get_me_endpoint(current_user=Depends(get_current_user)):
    """获取当前登录用户信息及多用户模式开关状态"""
    return {
        "user": current_user,
        "multi_user_mode": memory_manager.is_multi_user_mode(),
    }


@router.put("/auth/password")
async def change_own_password_endpoint(
    req: ChangePasswordRequest, current_user=Depends(get_current_user)
):
    """修改当前登录用户自己的密码"""
    if len(req.new_password or "") < 6:
        raise HTTPException(status_code=400, detail="新密码长度不能少于 6 位")

    user_secret = memory_manager.get_user_by_id(current_user["id"], include_secret=True)
    if not user_secret or not verify_password(
        req.old_password or "", user_secret["password_hash"], user_secret["salt"]
    ):
        raise HTTPException(status_code=400, detail="当前原密码输入错误")

    try:
        memory_manager.update_user(current_user["id"], new_password=req.new_password)
        return {"success": True, "message": "密码修改成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/admin/auth-mode")
async def update_auth_mode_endpoint(
    req: AuthModeRequest, admin_user=Depends(require_admin)
):
    """管理员：切换单人免登录模式 / 多用户鉴权模式"""
    enabled = memory_manager.set_multi_user_mode(bool(req.multi_user_mode))
    return {
        "success": True,
        "multi_user_mode": enabled,
        "message": "已开启多用户鉴权模式（未登录访问将返回 401）"
        if enabled
        else "已切回单人免登录模式（本地打开直接以管理员身份进入）",
    }


@router.get("/admin/users")
async def list_users_endpoint(admin_user=Depends(require_admin)):
    """管理员：获取所有用户列表"""
    return {
        "users": memory_manager.list_users(),
        "multi_user_mode": memory_manager.is_multi_user_mode(),
    }


@router.post("/admin/users")
async def create_user_endpoint(
    req: CreateUserRequest, admin_user=Depends(require_admin)
):
    """管理员：新建用户"""
    try:
        user = memory_manager.create_user(
            username=req.username,
            password=req.password,
            display_name=req.display_name,
            role=req.role,
        )
        return {"success": True, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/admin/users/{user_id}")
async def update_user_endpoint(
    user_id: str, req: UpdateUserRequest, admin_user=Depends(require_admin)
):
    """管理员：修改用户角色 / 启用禁用 / 显示名 / 重置密码"""
    target = memory_manager.get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 保护默认 admin 账号不被降级或禁用，避免锁死后台 (RK-06)
    if target["username"] == "admin":
        if req.role == "member":
            raise HTTPException(status_code=400, detail="不能将系统默认管理员 admin 降级为普通成员")
        if req.is_active is False:
            raise HTTPException(status_code=400, detail="不能禁用系统默认管理员 admin")

    try:
        updated = memory_manager.update_user(
            user_id=user_id,
            display_name=req.display_name,
            role=req.role,
            is_active=req.is_active,
            new_password=req.new_password,
        )
        return {"success": True, "user": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/admin/users/{user_id}")
async def delete_user_endpoint(
    user_id: str,
    strategy: str = Query("transfer", description="数据处理策略：transfer(转移给admin) / delete(一并删除)"),
    admin_user=Depends(require_admin),
):
    """管理员：删除用户（支持转移或级联删除数据，删除前自动备份数据库）"""
    if strategy not in ("transfer", "delete"):
        raise HTTPException(status_code=400, detail="strategy 仅支持 transfer 或 delete")
    if user_id == admin_user["id"]:
        raise HTTPException(status_code=400, detail="不能删除当前正在登录的管理员账号")

    try:
        result = memory_manager.delete_user(
            user_id=user_id,
            strategy=strategy,
            transfer_to_user_id=admin_user["id"],
        )
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

