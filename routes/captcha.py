# routes/captcha.py
from fastapi import APIRouter, Response
from captcha.image import ImageCaptcha
import random, string, io

router = APIRouter()

@router.get("/api/auth/captcha")
def get_captcha():
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    image = ImageCaptcha()
    data = image.generate(code)
    img_bytes = io.BytesIO(data.read())
    print(f"[验证码调试] 当前验证码为：{code}")
    return Response(content=img_bytes.getvalue(), media_type="image/png")
