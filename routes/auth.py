# routes/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time, jwt

SECRET_KEY = "stockscanner-secret"  # 建议放到 .env 文件

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str
    code: str

@router.post("/api/auth/login")
def login(data: LoginRequest):
    if data.username != "admin" or data.password != "123456":
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = jwt.encode({
        "sub": data.username,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600
    }, SECRET_KEY, algorithm="HS256")

    return {
        "token": token,
        "user": {
            "id": 1,
            "name": "管理员",
            "roles": ["admin"]
        }
    }
