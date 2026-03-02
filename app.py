from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- [ الإعدادات الخاصة بك ] ---
CLIENT_ID = "1453496208374108262"
CLIENT_SECRET = "DDf6GOxtdu_AOc5-FuZ8dJOWE19bO3F3"
# هذا الرابط سنغيره لاحقاً بعد رفع الموقع على Render
REDIRECT_URI = "https://riodashboard.onrender.com/callback" 

# رابط المونجو الذي استخرجته مع وضع كلمة السر الصحيحة
MONGO_URL = "mongodb+srv://rayendakli89_db_user:FSPThXDcqhw4X8ZS@cluster0.ineappi.mongodb.net/?appName=Cluster0"

# الاتصال بقاعدة البيانات
client = AsyncIOMotorClient(MONGO_URL)
db = client["EternalSilenceDB"]
collection = db["guilds_configs"]

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """الصفحة الرئيسية (الدخول)"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login():
    """توجيه المستخدم إلى ديسكورد لتسجيل الدخول"""
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
    """استقبال الكود من ديسكورد وتحويله إلى بيانات مستخدم"""
    async with httpx.AsyncClient() as http_client:
        # 1. تبديل الكود بـ Access Token
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
            return {"error": "فشل في الحصول على توكن الدخول"}

        # 2. جلب قائمة السيرفرات التي يتواجد بها المستخدم
        guilds_res = await http_client.get(
            "https://discord.com/api/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        guilds = guilds_res.json()

        # 3. تصفية السيرفرات (إظهار السيرفرات التي يمتلك فيها رتبة Administrator فقط)
        # الصلاحية رقم 0x8 هي صلاحية المسؤول (Administrator)
        admin_guilds = [
            g for g in guilds 
            if (int(g['permissions']) & 0x8) == 0x8
        ]

        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "guilds": admin_guilds
        })

@app.get("/settings/{guild_id}", response_class=HTMLResponse)
async def settings(request: Request, guild_id: str):
    """صفحة إعدادات سيرفر محدد"""
    # البحث عن إعدادات السيرفر في قاعدة البيانات
    config = await collection.find_one({"_id": int(guild_id)})
    
    # إذا لم يكن للسيرفر إعدادات، نضع إعدادات افتراضية للعرض فقط
    if not config:
        config = {"prefix": "=", "language": "ar"}


    return f"<h1>إعدادات السيرفر {guild_id}</h1><p>البريفكس الحالي: {config.get('prefix')}</p><a href='/'>عودة</a>"
