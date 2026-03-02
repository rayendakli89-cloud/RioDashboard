import os
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- [ الإعدادات - تقرأ من Render الآن ] ---
CLIENT_ID = os.getenv("CLIENT_ID", "1453496208374108262")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://riodashboard.onrender.com/callback")
MONGO_URL = os.getenv("MONGO_URL")

# الاتصال بقاعدة البيانات
client = AsyncIOMotorClient(MONGO_URL)
db = client["EternalSilenceDB"]
collection = db["guilds_configs"]

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login():
    discord_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify+guilds"
    )
    return RedirectResponse(discord_url)

@app.get("/callback")
async def callback(request: Request, code: str):
    async with httpx.AsyncClient() as http_client:
        token_data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
        token_res = await http_client.post("https://discord.com/api/oauth2/token", data=token_data)
        token_json = token_res.json()
        access_token = token_json.get("access_token")

        if not access_token:
            # سنطبع الخطأ في الـ Logs لنعرف السبب الحقيقي
            print(f"Token Error: {token_json}")
            return {"error": "فشل في الحصول على توكن الدخول", "details": token_json}

        guilds_res = await http_client.get(
            "https://discord.com/api/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        guilds = guilds_res.json()

        admin_guilds = [
            g for g in guilds 
            if (int(g.get('permissions', 0)) & 0x8) == 0x8
        ]

        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "guilds": admin_guilds
        })

@app.get("/settings/{guild_id}", response_class=HTMLResponse)
async def settings(request: Request, guild_id: str):
    config = await collection.find_one({"_id": int(guild_id)})
    if not config:
        config = {"prefix": "=", "language": "ar"}
    return f"<h1>إعدادات السيرفر {guild_id}</h1><p>البريفكس الحالي: {config.get('prefix')}</p><a href='/'>عودة</a>"
