import streamlit as st
from openai import OpenAI
from supabase import create_client
import uuid
import base64
from PIL import Image
from io import BytesIO
import hashlib
import datetime

# =====================
# PAGE CONFIG
# =====================
st.set_page_config(
    page_title="服裝 AI 設計系統",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================
# CUSTOM CSS
# =====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Sans:wght@300;400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp {
        background-color: #F8F6F2;
    }

    h1, h2, h3 {
        font-family: 'Cormorant Garamond', serif;
        font-weight: 300;
        letter-spacing: 0.05em;
    }

    .main-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 2.8rem;
        font-weight: 300;
        color: #1a1a1a;
        letter-spacing: 0.1em;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.85rem;
        color: #888;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-bottom: 2rem;
    }

    .style-card {
        border: 1px solid #E0DDD8;
        padding: 1.2rem;
        background: white;
        margin-bottom: 1rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .gallery-item {
        background: white;
        border: 1px solid #E0DDD8;
        padding: 0.8rem;
        margin-bottom: 1rem;
    }

    .tag {
        display: inline-block;
        background: #1a1a1a;
        color: white;
        padding: 0.2rem 0.8rem;
        font-size: 0.7rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    .divider {
        border: none;
        border-top: 1px solid #E0DDD8;
        margin: 1.5rem 0;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1a1a1a;
    }

    section[data-testid="stSidebar"] * {
        color: #F8F6F2 !important;
    }

    section[data-testid="stSidebar"] .stTextInput input {
        background: #2a2a2a;
        border: 1px solid #444;
        color: #F8F6F2 !important;
    }

    section[data-testid="stSidebar"] .stButton button {
        background: #F8F6F2;
        color: #1a1a1a !important;
        border: none;
        font-family: 'DM Sans', sans-serif;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        font-size: 0.8rem;
    }

    .stButton > button {
        background: #1a1a1a;
        color: white;
        border: none;
        padding: 0.7rem 2rem;
        font-family: 'DM Sans', sans-serif;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        font-size: 0.8rem;
        transition: all 0.2s ease;
        width: 100%;
    }

    .stButton > button:hover {
        background: #333;
        color: white;
    }

    .stSelectbox label, .stTextArea label, .stTextInput label, .stFileUploader label {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.75rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #666;
    }

    .stTextArea textarea, .stTextInput input {
        border: 1px solid #E0DDD8;
        border-radius: 0;
        font-family: 'DM Sans', sans-serif;
    }

    .stSelectbox select {
        border-radius: 0;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    .prompt-box {
        background: white;
        border: 1px solid #E0DDD8;
        padding: 1rem;
        font-family: 'Cormorant Garamond', serif;
        font-size: 1rem;
        font-style: italic;
        color: #444;
        line-height: 1.6;
        margin: 1rem 0;
    }

    .usage-counter {
        font-size: 0.75rem;
        color: #888;
        text-align: right;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)

# =====================
# CLIENTS (from secrets)
# =====================
@st.cache_resource
def get_clients():
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    supabase = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )
    return client, supabase

client, supabase = get_clients()

# =====================
# BASE PROMPT
# =====================
BASE_PROMPT = "professional fashion photography, high-end commercial, ultra detailed, 8k quality"

# =====================
# AUTH FUNCTIONS
# =====================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(email, password):
    """Check credentials against Supabase users table"""
    try:
        result = supabase.table("users").select("*").eq("email", email).execute()
        if not result.data:
            return False, None
        user = result.data[0]
        if user.get("password_hash") == hash_password(password):
            return True, user
        return False, None
    except Exception as e:
        st.error(f"Auth error: {e}")
        return False, None

def get_today_usage(email):
    """Count today's generations for this user"""
    try:
        today = datetime.date.today().isoformat()
        result = supabase.table("designs").select("id") \
            .eq("user_email", email) \
            .gte("created_at", f"{today}T00:00:00") \
            .execute()
        return len(result.data)
    except:
        return 0

# =====================
# IMAGE FUNCTIONS
# =====================
def upload_to_supabase(image_bytes):
    """Upload image bytes to Supabase Storage"""
    try:
        bucket = supabase.storage.from_("fashion-images")
        file_name = f"{uuid.uuid4()}.png"
        bucket.upload(file_name, image_bytes, {"content-type": "image/png"})
        return bucket.get_public_url(file_name)
    except Exception as e:
        st.warning(f"上傳警告：{e}")
        return None

# =====================
# MODEL CONFIG
# =====================
QUALITY_MODES = {
    "🌟 Ultra 高清（gpt-image-2 high）": {
        "generate_models": ["gpt-image-2", "gpt-image-1"],
        "edit_models":     ["gpt-image-2", "gpt-image-1", "dall-e-2"],
        "quality": "high",
        "desc": "最高畫質，細節最豐富，速度較慢、費用較高"
    },
    "✨ Ultra 標準（gpt-image-2 medium）": {
        "generate_models": ["gpt-image-2", "gpt-image-1", "dall-e-3"],
        "edit_models":     ["gpt-image-2", "gpt-image-1", "dall-e-2"],
        "quality": "medium",
        "desc": "最新模型，品質與速度平衡，不支援時自動降級"
    },
    "⚡ Standard（gpt-image-1）": {
        "generate_models": ["gpt-image-1", "dall-e-3"],
        "edit_models":     ["gpt-image-1", "dall-e-2"],
        "quality": "medium",
        "desc": "穩定品質，平衡速度"
    },
    "💨 Fast（dall-e-3）": {
        "generate_models": ["dall-e-3"],
        "edit_models":     ["dall-e-2"],
        "quality": None,
        "desc": "速度最快，無需特殊帳號權限"
    },
}

# =====================
# 長寬比設定
# =====================
ASPECT_RATIOS = {
    "1:1  正方形":   {"label": "⬜ 1:1",  "desc": "通用商品圖、社群貼文",          "ratio": (1, 1)},
    "4:3  橫式":     {"label": "🖼 4:3",  "desc": "商品展示、簡報用圖",            "ratio": (4, 3)},
    "3:2  橫式":     {"label": "🖼 3:2",  "desc": "一般攝影比例、官網圖",          "ratio": (3, 2)},
    "16:9 橫式寬螢幕": {"label": "🖥 16:9", "desc": "廣告橫幅、YouTube縮圖",         "ratio": (16, 9)},
    "21:9 超寬":     {"label": "🎬 21:9", "desc": "電影比例、全版廣告",            "ratio": (21, 9)},
    "3:4  直式":     {"label": "📱 3:4",  "desc": "雜誌封面、Pinterest",          "ratio": (3, 4)},
    "2:3  直式":     {"label": "📱 2:3",  "desc": "海報、DM 印刷",               "ratio": (2, 3)},
    "9:16 直式社群":  {"label": "📱 9:16", "desc": "Instagram Reels、TikTok",      "ratio": (9, 16)},
    "9:21 超直式":   {"label": "📱 9:21", "desc": "手機全版廣告",                 "ratio": (9, 21)},
}

# =====================
# 解析度等級
# gpt-image-2: 任意解析度，2K 穩定，4K 實驗性
# gpt-image-1: 1024x1024, 1536x1024, 1024x1536, auto
# dall-e-3:    1024x1024, 1792x1024, 1024x1792
# dall-e-2:    256x256, 512x512, 1024x1024
# =====================
RESOLUTION_TIERS = {
    "🟢 草稿  512px":   {"base": 512,  "desc": "快速預覽，速度最快",            "experimental": False},
    "⬜ 標準  1K":      {"base": 1024, "desc": "一般社群用途",                  "experimental": False},
    "🔵 高清  1.5K":    {"base": 1536, "desc": "高品質商品圖",                 "experimental": False},
    "🟡 2K   2560px":  {"base": 2560, "desc": "大圖輸出、印刷用（需帳號驗證）",  "experimental": True},
    "🔴 4K   3840px":  {"base": 3840, "desc": "超高清輸出（實驗性，需帳號驗證）", "experimental": True},
}

def calc_size(ratio_tuple, base_px):
    """根據長寬比和基準邊長計算實際像素，符合 gpt-image-2 規則"""
    w_ratio, h_ratio = ratio_tuple
    # 以較長邊為 base_px 計算
    if w_ratio >= h_ratio:
        w = base_px
        h = round(base_px * h_ratio / w_ratio)
    else:
        h = base_px
        w = round(base_px * w_ratio / h_ratio)
    # 確保兩邊都在 64~4096 之間，且為偶數
    w = max(64, min(4096, w - w % 2))
    h = max(64, min(4096, h - h % 2))
    return f"{w}x{h}"

def get_size_for_model(model, ratio_key, res_key):
    """根據 model 能力回傳最適合的 size 字串"""
    ratio = ASPECT_RATIOS[ratio_key]["ratio"]
    base  = RESOLUTION_TIERS[res_key]["base"]

    if model.startswith("gpt-image-2"):
        # gpt-image-2 支援任意解析度
        return calc_size(ratio, base)

    elif model.startswith("gpt-image-1"):
        # gpt-image-1 只支援固定三種尺寸
        w_r, h_r = ratio
        if w_r == h_r:
            return "1024x1024"
        elif w_r > h_r:
            return "1536x1024"
        else:
            return "1024x1536"

    elif model == "dall-e-3":
        w_r, h_r = ratio
        if w_r == h_r:
            return "1024x1024"
        elif w_r > h_r:
            return "1792x1024"
        else:
            return "1024x1792"

    else:  # dall-e-2
        return "1024x1024"  # dall-e-2 最大只有 1024

def _decode_result(result):
    """Extract bytes from API result (b64_json or url)"""
    import requests as req
    item = result.data[0]
    if hasattr(item, "b64_json") and item.b64_json:
        return base64.b64decode(item.b64_json)
    elif hasattr(item, "url") and item.url:
        return req.get(item.url).content
    raise ValueError("No image data in response")

def generate_image_from_prompt(full_prompt, quality_key="✨ Ultra 標準（gpt-image-2 medium）", ratio_key="1:1  正方形", res_key="⬜ 標準  1K"):
    """Try models in order, fallback automatically."""
    mode = QUALITY_MODES[quality_key]
    img_quality = mode.get("quality")
    errors = []

    for model in mode["generate_models"]:
        try:
            model_size = get_size_for_model(model, ratio_key, res_key)
            kwargs = dict(model=model, prompt=full_prompt, size=model_size)
            if img_quality and model.startswith("gpt-image"):
                kwargs["quality"] = img_quality
            if model == "dall-e-3":
                kwargs["response_format"] = "b64_json"
            result = client.images.generate(**kwargs)
            q_label = f"｜{img_quality}" if img_quality and model.startswith("gpt-image") else ""
            st.caption(f"✓ **{model}**（{model_size}{q_label}）")
            return _decode_result(result)
        except Exception as e:
            errors.append(f"{model}: {e}")
            continue

    raise Exception("All models failed:\n" + "\n".join(errors))

def generate_image_from_reference(reference_bytes, full_prompt, quality_key="✨ Ultra 標準（gpt-image-2 medium）", ratio_key="1:1  正方形", res_key="⬜ 標準  1K"):
    """Edit reference image."""
    errors = []

    img = Image.open(BytesIO(reference_bytes)).convert("RGBA")
    buf = BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    mode = QUALITY_MODES[quality_key]
    img_quality = mode.get("quality")
    edit_models = mode["edit_models"]

    for model in edit_models:
        try:
            model_size = get_size_for_model(model, ratio_key, res_key)
            png_file = ("image.png", BytesIO(png_bytes), "image/png")
            kwargs = dict(model=model, image=png_file, prompt=full_prompt, size=model_size)
            if img_quality and model.startswith("gpt-image"):
                kwargs["quality"] = img_quality
            if model in ("dall-e-2", "dall-e-3"):
                kwargs["response_format"] = "b64_json"
            result = client.images.edit(**kwargs)
            q_label = f"｜{img_quality}" if img_quality and model.startswith("gpt-image") else ""
            st.caption(f"✓ **{model}** 編輯（{model_size}{q_label}）")
            return _decode_result(result)
        except Exception as e:
            errors.append(f"{model}: {e}")
            continue

    raise Exception("All models failed:\n" + "\n".join(errors))

def save_design(email, prompt, style, image_url):
    """Save design record to Supabase"""
    try:
        supabase.table("designs").insert({
            "user_email": email,
            "prompt": prompt,
            "style": style,
            "image_url": image_url
        }).execute()
    except Exception as e:
        st.warning(f"儲存警告：{e}")

def build_prompt(user_input):
    """Build prompt from user input"""
    return f"{BASE_PROMPT}, {user_input}"


def get_ai_feedback(original_prompt, edit_history):
    """用 Claude/OpenAI 分析目前圖片狀況，給出具體修改建議"""
    import requests as _req

    history_text = ""
    for i, h in enumerate(edit_history):
        history_text += f"\n  第{i+1}版：{h['prompt']}"

    system = """你是一位專業的時尚設計顧問 AI。
用戶正在使用 AI 生成服裝設計圖，你需要根據他們的設計描述和修改歷史，
提供 3 條具體、實用的下一步修改建議。

規則：
- 每條建議必須是一句具體的修改指令（20字以內）
- 不要說廢話，直接給建議
- 根據設計脈絡給相關建議
- 回傳 JSON 格式：{"suggestions": ["建議1", "建議2", "建議3"], "comment": "一句簡短點評"}
- 只回傳 JSON，不要其他文字"""

    user_msg = f"""原始設計描述：{original_prompt}
修改歷史：{history_text if history_text else "（尚無修改）"}

請給出 3 條下一步修改建議。"""

    try:
        resp = _req.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": st.secrets.get("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 300,
                "system": system,
                "messages": [{"role": "user", "content": user_msg}]
            },
            timeout=15
        )
        if resp.status_code == 200:
            import json as _json
            text = resp.json()["content"][0]["text"].strip()
            return _json.loads(text)
    except Exception:
        pass

    # fallback：用 OpenAI
    try:
        resp2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_msg}
            ],
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        import json as _json
        return _json.loads(resp2.choices[0].message.content)
    except Exception:
        pass

    return None

# =====================
# LOGIN PAGE
# =====================
def show_login():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<br><br>', unsafe_allow_html=True)
        st.markdown('<p class="main-title" style="text-align:center">Fashion AI</p>', unsafe_allow_html=True)
        st.markdown('<p class="subtitle" style="text-align:center">公司內部設計系統</p>', unsafe_allow_html=True)
        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@company.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("進入系統")

            if submitted:
                if not email or not password:
                    st.error("請輸入 Email 和密碼")
                else:
                    with st.spinner("Authenticating..."):
                        ok, user = authenticate(email, password)
                    if ok:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user
                        st.session_state["email"] = email
                        st.rerun()
                    else:
                        st.error("帳號或密碼錯誤，請重試")

        st.markdown('<br><p style="text-align:center;font-size:0.75rem;color:#aaa;">帳號問題請聯繫 IT 管理員</p>', unsafe_allow_html=True)

# =====================
# MAIN APP
# =====================
def show_app():
    email = st.session_state["email"]
    user = st.session_state["user"]
    daily_limit = user.get("daily_limit", 20)

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown('<br>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-family:Cormorant Garamond,serif;font-size:1.4rem;font-weight:300;letter-spacing:0.1em;">Fashion AI Studio</p>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:0.75rem;opacity:0.6;letter-spacing:0.05em;">Welcome, {user.get("name", email.split("@")[0])}</p>', unsafe_allow_html=True)

        st.markdown("---")

        usage = get_today_usage(email)
        pct = int((usage / daily_limit) * 100)
        st.markdown(f'<p style="font-size:0.75rem;opacity:0.7;letter-spacing:0.05em;">今日使用：{usage}/{daily_limit}</p>', unsafe_allow_html=True)
        st.progress(min(pct / 100, 1.0))

        st.markdown("---")

        is_admin = user.get("role") == "admin"

        nav_options = ["✦ 生成圖片", "📋 我的紀錄"]
        if is_admin:
            nav_options += ["🖼 全體圖庫", "👥 員工管理"]

        nav = st.radio("Navigation", nav_options, label_visibility="collapsed")

        st.markdown("---")

        if is_admin:
            st.markdown('<p style="font-size:0.7rem;letter-spacing:0.08em;color:#aaa;text-transform:uppercase;">管理員模式</p>', unsafe_allow_html=True)
            st.markdown("---")

        if st.button("登出"):
            for key in ["authenticated", "user", "email"]:
                st.session_state.pop(key, None)
            st.rerun()

    # --- MAIN CONTENT ---
    if "✦ 生成圖片" in nav:
        show_generate(email, usage, daily_limit)
    elif "📋 我的紀錄" in nav:
        show_history(email)
    elif "🖼 全體圖庫" in nav and is_admin:
        show_gallery_admin()
    elif "👥 員工管理" in nav and is_admin:
        show_user_management()


def _render_settings_panel(quality_key, ratio_key, res_key):
    """右側輸出設定總覽 box"""
    qmode = QUALITY_MODES.get(quality_key, {})
    models_str = " → ".join(qmode.get("generate_models", []))
    img_quality = qmode.get("quality")
    quality_label = {"high": "🔴 高清 High", "medium": "🟡 標準 Medium", "low": "🟢 快速 Low"}.get(img_quality, "—")
    first_model = qmode.get("generate_models", ["dall-e-3"])[0]
    preview_size = get_size_for_model(first_model, ratio_key, res_key)
    pw, ph = preview_size.split("x")
    orient = "橫式" if int(pw) > int(ph) else ("直式" if int(ph) > int(pw) else "正方形")
    ratio_icon = ASPECT_RATIOS[ratio_key]["label"]
    exp_tag = " ⚠️ 實驗性" if RESOLUTION_TIERS[res_key]["experimental"] else ""
    st.markdown(
        f'<div style="background:#f5f3ef;border:1px solid #E0DDD8;padding:1rem;margin-bottom:1rem;">'
        f'<div style="font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase;color:#888;margin-bottom:0.6rem;">輸出設定總覽</div>'
        f'<div style="font-size:0.8rem;color:#333;font-family:monospace;margin-bottom:0.3rem;">{models_str}</div>'
        f'<div style="font-size:0.75rem;color:#555;margin-top:0.3rem;">{ratio_icon} &nbsp;{ratio_key.strip()}</div>'
        f'<div style="font-size:0.75rem;color:#555;margin-top:0.2rem;">📐 {preview_size} &nbsp;｜&nbsp; {orient}{exp_tag}</div>'
        f'<div style="font-size:0.75rem;color:#555;margin-top:0.2rem;">✦ 畫質：{quality_label}</div>'
        f'</div>',
        unsafe_allow_html=True
    )


def _render_chat_history():
    """顯示對話式編輯歷史"""
    history = st.session_state.get("edit_history", [])
    if not history:
        return
    st.markdown("---")
    st.markdown("#### 📜 本次編輯歷史")
    for i, item in enumerate(history):
        with st.expander(f"第 {i+1} 版 — {item['label']}", expanded=(i == len(history)-1)):
            st.image(item["bytes"], use_container_width=True)
            st.caption(item["prompt"])
            dl_col, _ = st.columns([1, 2])
            with dl_col:
                st.download_button(
                    f"⬇ 下載第 {i+1} 版",
                    data=item["bytes"],
                    file_name=f"fashion_v{i+1}_{uuid.uuid4().hex[:6]}.png",
                    mime="image/png",
                    key=f"hist_dl_{i}"
                )


def show_generate(email, usage, daily_limit):
    st.markdown('<p class="main-title">設計工作室</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">AI 服裝形象圖生成</p>', unsafe_allow_html=True)

    remaining = daily_limit - usage
    if remaining <= 0:
        st.error(f"您今日已達 {daily_limit} 張上限，請明日再試")
        return

    # ── Session state 初始化 ──
    for k, v in [("current_img", None), ("edit_history", []), ("quick_cmd", "")]:
        if k not in st.session_state:
            st.session_state[k] = v

    has_current = st.session_state["current_img"] is not None

    # ════════════════════════════════════════════
    # 區塊一：設定 + 生成
    # ════════════════════════════════════════════
    with st.container():
        col1, col2 = st.columns([1.1, 1], gap="large")

        with col1:
            quality_key = st.selectbox("畫質／模型", list(QUALITY_MODES.keys()),
                help="Ultra 會自動嘗試最新模型，不支援時自動降級", key="qk_new")
            st.caption(f"　{QUALITY_MODES[quality_key]['desc']}")

            ratio_key = st.selectbox("長寬比", list(ASPECT_RATIOS.keys()),
                help="選擇圖片的長寬比例", key="rk_new")
            st.caption(f"　{ASPECT_RATIOS[ratio_key]['desc']}")

            res_key = st.selectbox("解析度", list(RESOLUTION_TIERS.keys()), index=1,
                help="2K/4K 需要帳號驗證，屬實驗性功能", key="rek_new")
            res_info = RESOLUTION_TIERS[res_key]
            st.caption(f"　{'⚠️ ' if res_info['experimental'] else ''}{res_info['desc']}")

            user_prompt = st.text_area("設計描述",
                placeholder="例如：將所有圖片的裙子改成紅色、換成絨布材質...",
                height=120, key="prompt_new")

            # ── 多圖上傳 ──
            st.markdown('<p style="font-size:0.75rem;color:#888;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.3rem;">上傳圖片（可多選，最多10張）</p>', unsafe_allow_html=True)
            reference_files = st.file_uploader(
                "拖曳或點擊上傳",
                type=["png","jpg","jpeg"],
                accept_multiple_files=True,
                key="ref_multi",
                label_visibility="collapsed"
            )

            # 預覽上傳的圖片
            if reference_files:
                st.markdown(f'<p style="font-size:0.8rem;color:#555;">已上傳 {len(reference_files)} 張圖片</p>', unsafe_allow_html=True)
                prev_cols = st.columns(min(len(reference_files), 5))
                for pi, rf in enumerate(reference_files[:5]):
                    with prev_cols[pi]:
                        st.image(rf.getvalue(), use_container_width=True, caption=rf.name[:12])
                if len(reference_files) > 5:
                    st.caption(f"...還有 {len(reference_files)-5} 張")

        with col2:
            _render_settings_panel(quality_key, ratio_key, res_key)
            st.markdown(f'<p class="usage-counter">今日剩餘：{remaining} 張</p>', unsafe_allow_html=True)

            # 計算將消耗的額度
            n_refs = len(reference_files) if reference_files else 0
            if n_refs > 0:
                cost_count = n_refs
                st.info(f"📌 將對 {n_refs} 張上傳圖片各套用一次描述詞，共消耗 {n_refs} 張額度")
            else:
                num_images = st.selectbox("生成數量", [1,2,3,4,5,6,8,10], index=0,
                    help="無上傳圖片時，直接生成指定數量", key="num_new")
                cost_count = num_images

            if cost_count > remaining:
                st.warning(f"今日剩餘 {remaining} 張，請減少上傳數量或生成數量")

            generate_btn = st.button("✦ 開始處理", use_container_width=True, key="gen_new",
                type="primary")

        # ── 生成邏輯 ──
        if generate_btn:
            if not user_prompt.strip():
                st.warning("請輸入描述詞")
            elif cost_count > remaining:
                st.error(f"今日剩餘額度不足（剩 {remaining} 張）")
            else:
                full_prompt = build_prompt(user_prompt)
                st.session_state["edit_history"] = []
                st.session_state["current_img"]  = None
                results = []  # [(img_bytes, label)]

                if reference_files:
                    # ── 模式A：多圖批次處理 ──
                    prog = st.progress(0, text="準備中...")
                    for i, rf in enumerate(reference_files):
                        prog.progress((i) / len(reference_files),
                            text=f"處理第 {i+1} / {len(reference_files)} 張：{rf.name[:20]}")
                        try:
                            img_bytes = generate_image_from_reference(
                                rf.getvalue(), full_prompt, quality_key, ratio_key, res_key)
                            results.append((img_bytes, rf.name))
                            url = upload_to_supabase(img_bytes)
                            save_design(email, full_prompt, "", url)
                        except Exception as e:
                            st.error(f"「{rf.name}」處理失敗：{e}")
                    prog.progress(1.0, text=f"✓ 完成 {len(results)} / {len(reference_files)} 張")

                else:
                    # ── 模式B：純文字生成多張 ──
                    for i in range(num_images):
                        label = f"第 {i+1} / {num_images} 張" if num_images > 1 else "生成中"
                        with st.spinner(f"AI 生成中：{label}，請稍候..."):
                            try:
                                img_bytes = generate_image_from_prompt(full_prompt, quality_key, ratio_key, res_key)
                                results.append((img_bytes, f"生成第{i+1}張"))
                                url = upload_to_supabase(img_bytes)
                                save_design(email, full_prompt, "", url)
                            except Exception as e:
                                st.error(f"第 {i+1} 張生成失敗：{e}")

                # ── 顯示結果 ──
                if results:
                    st.success(f"✓ 成功處理 {len(results)} 張，已儲存至圖庫")

                    if len(results) == 1:
                        # 單張 → 直接進入修改模式
                        st.session_state["current_img"] = results[0][0]
                        st.session_state["edit_history"] = [{
                            "bytes": results[0][0],
                            "prompt": full_prompt,
                            "label": "v1 原始生成"
                        }]
                        st.rerun()
                    else:
                        # 多張 → grid 顯示，每張可選擇繼續修改
                        st.markdown("---")
                        st.markdown("#### 處理結果")
                        gcols = st.columns(3)
                        for idx, (ib, lbl) in enumerate(results):
                            with gcols[idx % 3]:
                                st.image(ib, caption=lbl, use_container_width=True)
                                dc, sc = st.columns(2)
                                with dc:
                                    st.download_button(
                                        "⬇ 下載",
                                        data=ib,
                                        file_name=f"fashion_{lbl[:10].replace('.','_')}_{uuid.uuid4().hex[:4]}.png",
                                        mime="image/png",
                                        key=f"dl_new_{idx}"
                                    )
                                with sc:
                                    if st.button("✏️ 繼續修改", key=f"sel_{idx}",
                                                 use_container_width=True):
                                        st.session_state["current_img"] = ib
                                        st.session_state["edit_history"] = [{
                                            "bytes": ib,
                                            "prompt": full_prompt,
                                            "label": f"v1 — {lbl[:20]}"
                                        }]
                                        st.rerun()

    # ════════════════════════════════════════════
    # 區塊二：目前圖片 + 修改區（生成後自動出現）
    # ════════════════════════════════════════════
    if has_current:
        current_bytes = st.session_state["current_img"]
        history       = st.session_state["edit_history"]
        version       = len(history)

        st.markdown("---")

        # 版本標題列
        ver_col, clear_col = st.columns([4, 1])
        with ver_col:
            st.markdown(
                f'<div style="background:#1a1a1a;color:white;padding:0.6rem 1rem;font-size:0.8rem;'
                f'letter-spacing:0.1em;text-transform:uppercase;">'
                f'目前版本：第 {version} 版 &nbsp;｜&nbsp; 共修改 {version-1} 次'
                f'</div>',
                unsafe_allow_html=True
            )
        with clear_col:
            if st.button("🗑 清空重來", use_container_width=True, key="clear_edit"):
                st.session_state["current_img"]  = None
                st.session_state["edit_history"] = []
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        img_col, edit_col = st.columns([1, 1], gap="large")

        # ── 左側：目前圖片 ──
        with img_col:
            st.image(current_bytes, caption=f"第 {version} 版", use_container_width=True)
            st.download_button("⬇ 下載目前版本", data=current_bytes,
                file_name=f"fashion_v{version}_{uuid.uuid4().hex[:6]}.png",
                mime="image/png", key="dl_current")

        # ── 右側：修改指令 ──
        with edit_col:
            st.markdown("#### ✏️ 修改指令")

            # ── AI 建議回饋區 ──
            if "ai_feedback" not in st.session_state:
                st.session_state["ai_feedback"] = None

            # 每次版本更新就重新取得建議
            feedback_version_key = f"feedback_v{version}"
            if st.session_state.get("feedback_version") != feedback_version_key:
                with st.spinner("AI 分析中，產生修改建議..."):
                    origin_prompt = history[0]["prompt"] if history else ""
                    fb = get_ai_feedback(origin_prompt, history)
                    st.session_state["ai_feedback"] = fb
                    st.session_state["feedback_version"] = feedback_version_key

            fb = st.session_state.get("ai_feedback")
            if fb:
                comment = fb.get("comment", "")
                suggestions = fb.get("suggestions", [])

                if comment:
                    st.markdown(
                        f'<div style="background:#f0f7ff;border-left:3px solid #4A90D9;'
                        f'padding:0.7rem 1rem;margin-bottom:0.8rem;font-size:0.85rem;color:#333;">'
                        f'💬 {comment}</div>',
                        unsafe_allow_html=True
                    )

                if suggestions:
                    st.markdown('<p style="font-size:0.75rem;color:#888;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.4rem;">AI 建議修改</p>', unsafe_allow_html=True)
                    for si, sug in enumerate(suggestions):
                        if st.button(f"✦ {sug}", key=f"sug_{version}_{si}", use_container_width=True):
                            st.session_state["quick_cmd"] = sug
                            st.rerun()

            st.markdown("---")

            # 快速指令
            st.markdown('<p style="font-size:0.75rem;color:#888;letter-spacing:0.08em;text-transform:uppercase;">快速指令</p>', unsafe_allow_html=True)
            quick_cmds = [
                ("🖤 換黑色", "將服裝改為黑色"),
                ("🤍 換白色", "將服裝改為白色"),
                ("❤️ 換紅色", "將服裝改為深紅色"),
                ("🌸 加蕾絲", "加入精緻蕾絲裝飾"),
                ("🪡 加刺繡", "加入花卉刺繡細節"),
                ("👗 改短裙", "將裙擺改為短裙"),
                ("🧥 加外套", "搭配俐落外套"),
                ("⬜ 白背景", "改為純白底背景"),
            ]
            qcols = st.columns(4)
            for qi, (btn_label, cmd) in enumerate(quick_cmds):
                with qcols[qi % 4]:
                    if st.button(btn_label, key=f"qcmd_{qi}", use_container_width=True):
                        st.session_state["quick_cmd"] = cmd
                        st.rerun()

            edit_prompt = st.text_area(
                "或自行輸入修改指令",
                value=st.session_state.get("quick_cmd", ""),
                placeholder="例如：把裙子改成紅色、換成絨布材質、加上肩帶...",
                height=90,
                key="edit_prompt_input"
            )

            if st.session_state.get("quick_cmd") and edit_prompt:
                st.session_state["quick_cmd"] = ""

            st.markdown(f'<p class="usage-counter">今日剩餘：{remaining} 張</p>', unsafe_allow_html=True)

            edit_btn = st.button("✏️ 套用修改", use_container_width=True,
                key="edit_apply", type="primary")

            if edit_btn:
                if not edit_prompt.strip():
                    st.warning("請輸入修改指令")
                elif remaining <= 0:
                    st.error("今日額度已用完")
                else:
                    # 繼承上一版的畫質設定
                    eq_key   = st.session_state.get("qk_new", list(QUALITY_MODES.keys())[1])
                    er_key   = st.session_state.get("rk_new", list(ASPECT_RATIOS.keys())[0])
                    erez_key = st.session_state.get("rek_new", list(RESOLUTION_TIERS.keys())[1])

                    with st.spinner(f"AI 修改中（生成第 {version+1} 版），請稍候..."):
                        try:
                            new_bytes = generate_image_from_reference(
                                current_bytes, build_prompt(edit_prompt),
                                eq_key, er_key, erez_key)
                            st.session_state["current_img"] = new_bytes
                            st.session_state["edit_history"].append({
                                "bytes":  new_bytes,
                                "prompt": edit_prompt,
                                "label":  f"v{version+1} — {edit_prompt[:30]}"
                            })
                            st.session_state["quick_cmd"] = ""
                            st.session_state["ai_feedback"] = None  # 觸發重新取得建議
                            url = upload_to_supabase(new_bytes)
                            save_design(email, edit_prompt, "edit", url)
                            st.success(f"✓ 第 {version+1} 版完成")
                            st.rerun()
                        except Exception as e:
                            st.error(f"修改失敗：{e}")

        # ── 歷史版本 ──
        if len(history) > 1:
            st.markdown("---")
            st.markdown("#### 📜 所有版本")
            hcols = st.columns(min(len(history), 4))
            for i, item in enumerate(history):
                with hcols[i % 4]:
                    st.image(item["bytes"], caption=item["label"], use_container_width=True)
                    dl_col, sel_col = st.columns(2)
                    with dl_col:
                        st.download_button("⬇", data=item["bytes"],
                            file_name=f"fashion_{item['label'][:10].replace(' ','_')}_{uuid.uuid4().hex[:4]}.png",
                            mime="image/png", key=f"hist_dl_{i}")
                    with sel_col:
                        if st.button("↩ 回此版", key=f"hist_sel_{i}", use_container_width=True):
                            st.session_state["current_img"] = item["bytes"]
                            st.session_state["edit_history"] = history[:i+1]
                            st.rerun()


def show_gallery_admin():
    """管理員專用：查看全體圖庫，含詳細資訊"""
    st.markdown('<p class="main-title">全體圖庫</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">管理員檢視 — 所有員工生成紀錄</p>', unsafe_allow_html=True)

    col_search, col_user = st.columns([2, 1])
    with col_search:
        search = st.text_input("搜尋", placeholder="搜尋 prompt 關鍵字...")
    with col_user:
        try:
            all_users = supabase.table("users").select("email,name").execute()
            user_emails = ["全部員工"] + [u.get("email","") for u in (all_users.data or [])]
        except:
            user_emails = ["全部員工"]
        filter_user = st.selectbox("篩選員工", user_emails)

    try:
        data = supabase.table("designs").select("*").order("created_at", desc=True).limit(200).execute()
        items = data.data or []
    except Exception as e:
        st.error(f"圖庫載入失敗：{e}")
        return

    if search:
        items = [i for i in items if search.lower() in (i.get("prompt","")).lower()]
    if filter_user != "全部員工":
        items = [i for i in items if i.get("user_email") == filter_user]

    valid_items = [i for i in items if i.get("image_url")]

    if not valid_items:
        st.info("尚無圖片")
        return

    # 統計列
    emails = [i.get("user_email","") for i in valid_items]
    unique_users = len(set(emails))
    st.markdown(
        f'<div style="display:flex;gap:2rem;margin-bottom:1rem;">'
        f'<div style="font-size:0.8rem;color:#888;">共 <b>{len(valid_items)}</b> 張圖片</div>'
        f'<div style="font-size:0.8rem;color:#888;">來自 <b>{unique_users}</b> 位員工</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    cols = st.columns(3)
    for idx, item in enumerate(valid_items):
        with cols[idx % 3]:
            try:
                st.image(item["image_url"], use_container_width=True)
                creator_email = item.get("user_email", "")
                creator_name  = creator_email.split("@")[0]
                created_at    = item.get("created_at","")[:16].replace("T"," ")
                prompt_text   = item.get("prompt","")
                st.markdown(
                    f'<div style="background:white;border:1px solid #E0DDD8;padding:0.6rem;margin-bottom:0.5rem;">'
                    f'<div style="font-size:0.7rem;color:#888;">👤 {creator_name} &nbsp;｜&nbsp; 🕐 {created_at}</div>'
                    f'<div style="font-size:0.75rem;color:#555;margin-top:0.3rem;">{prompt_text[:100]}{"..." if len(prompt_text)>100 else ""}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            except:
                pass


def show_history(email):
    st.markdown('<p class="main-title">我的生成紀錄</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">個人作品紀錄</p>', unsafe_allow_html=True)

    try:
        data = supabase.table("designs").select("*").eq("user_email", email).order("created_at", desc=True).limit(50).execute()
        items = [i for i in (data.data or []) if i.get("image_url")]
    except Exception as e:
        st.error(f"紀錄載入失敗：{e}")
        return

    if not items:
        st.info("您還沒有生成過任何圖片，前往「生成圖片」開始使用！")
        return

    st.markdown(f'<p style="font-size:0.8rem;color:#888;">{len(items)} 張生成紀錄</p>', unsafe_allow_html=True)

    cols = st.columns(3)
    for idx, item in enumerate(items):
        with cols[idx % 3]:
            try:
                st.image(item["image_url"], use_container_width=True)
                created = item.get("created_at","")[:16].replace("T"," ")
                prompt_short = item.get("prompt","")[:80]
                st.markdown(
                    f'<div style="font-size:0.75rem;color:#888;margin-top:0.2rem;">🕐 {created}</div>'
                    f'<div style="font-size:0.75rem;color:#555;margin-top:0.2rem;">{prompt_short}{"..." if len(item.get("prompt",""))>80 else ""}</div>',
                    unsafe_allow_html=True
                )
                st.markdown("---")
            except:
                pass


# =====================
# 員工管理（管理員專用）
# =====================
def show_user_management():
    st.markdown('<p class="main-title">員工管理</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">管理員專用 — 帳號與權限設定</p>', unsafe_allow_html=True)

    try:
        result = supabase.table("users").select("*").order("created_at", desc=True).execute()
        users = result.data or []
    except Exception as e:
        st.error(f"載入失敗：{e}")
        return

    # ── 統計列 ──
    admins    = sum(1 for u in users if u.get("role") == "admin")
    designers = sum(1 for u in users if u.get("role") != "admin")
    st.markdown(
        f'<div style="display:flex;gap:2rem;margin-bottom:1.5rem;">'
        f'<div style="background:white;border:1px solid #E0DDD8;padding:0.8rem 1.5rem;"><div style="font-size:1.4rem;font-weight:300;">{len(users)}</div><div style="font-size:0.7rem;color:#888;text-transform:uppercase;letter-spacing:0.08em;">總員工數</div></div>'
        f'<div style="background:white;border:1px solid #E0DDD8;padding:0.8rem 1.5rem;"><div style="font-size:1.4rem;font-weight:300;">{designers}</div><div style="font-size:0.7rem;color:#888;text-transform:uppercase;letter-spacing:0.08em;">設計師</div></div>'
        f'<div style="background:white;border:1px solid #E0DDD8;padding:0.8rem 1.5rem;"><div style="font-size:1.4rem;font-weight:300;">{admins}</div><div style="font-size:0.7rem;color:#888;text-transform:uppercase;letter-spacing:0.08em;">管理員</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    tab1, tab2, tab3 = st.tabs(["📋 員工列表", "➕ 新增員工", "🔑 修改密碼"])

    # ══ TAB 1：員工列表 ══
    with tab1:
        for u in users:
            with st.expander(f"{'👑' if u.get('role')=='admin' else '👤'}  {u.get('name','—')}  ／  {u.get('email','')}"):
                c1, c2, c3 = st.columns(3)
                uid = u["id"]

                with c1:
                    new_name = st.text_input("姓名", value=u.get("name",""), key=f"name_{uid}")
                with c2:
                    role_options = ["designer", "admin"]
                    cur_role = u.get("role","designer")
                    new_role = st.selectbox("權限", role_options,
                        index=role_options.index(cur_role) if cur_role in role_options else 0,
                        key=f"role_{uid}")
                with c3:
                    new_limit = st.number_input("每日額度", min_value=1, max_value=500,
                        value=int(u.get("daily_limit", 20)), step=5, key=f"limit_{uid}")

                col_save, col_del = st.columns([3, 1])
                with col_save:
                    if st.button("💾 儲存變更", key=f"save_{uid}"):
                        try:
                            supabase.table("users").update({
                                "name": new_name,
                                "role": new_role,
                                "daily_limit": new_limit
                            }).eq("id", uid).execute()
                            st.success("✓ 已更新")
                            st.rerun()
                        except Exception as e:
                            st.error(f"更新失敗：{e}")
                with col_del:
                    if st.button("🗑 刪除", key=f"del_{uid}", type="secondary"):
                        try:
                            supabase.table("users").delete().eq("id", uid).execute()
                            st.success("已刪除")
                            st.rerun()
                        except Exception as e:
                            st.error(f"刪除失敗：{e}")

    # ══ TAB 2：新增員工 ══
    with tab2:
        st.markdown("#### 新增員工帳號")
        with st.form("add_user_form"):
            new_email = st.text_input("Email *")
            new_name  = st.text_input("姓名")
            new_pw    = st.text_input("密碼 *", type="password")
            new_role  = st.selectbox("權限", ["designer", "admin"])
            new_limit = st.number_input("每日額度", min_value=1, max_value=500, value=20, step=5)
            submitted = st.form_submit_button("➕ 新增")

            if submitted:
                if not new_email or not new_pw:
                    st.error("Email 和密碼為必填")
                else:
                    import hashlib as _hl
                    pw_hash = _hl.sha256(new_pw.encode()).hexdigest()
                    try:
                        supabase.table("users").insert({
                            "email": new_email,
                            "name": new_name,
                            "password_hash": pw_hash,
                            "role": new_role,
                            "daily_limit": new_limit
                        }).execute()
                        st.success(f"✓ 已新增 {new_email}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"新增失敗（Email 可能重複）：{e}")

    # ══ TAB 3：修改密碼 ══
    with tab3:
        st.markdown("#### 重設員工密碼")
        user_emails = [u.get("email","") for u in users]
        target_email = st.selectbox("選擇員工", user_emails)
        new_pw1 = st.text_input("新密碼", type="password", key="pw1")
        new_pw2 = st.text_input("確認新密碼", type="password", key="pw2")

        if st.button("🔑 更新密碼"):
            if not new_pw1:
                st.error("請輸入新密碼")
            elif new_pw1 != new_pw2:
                st.error("兩次密碼不一致")
            else:
                import hashlib as _hl
                pw_hash = _hl.sha256(new_pw1.encode()).hexdigest()
                try:
                    supabase.table("users").update({"password_hash": pw_hash}).eq("email", target_email).execute()
                    st.success(f"✓ {target_email} 密碼已更新")
                except Exception as e:
                    st.error(f"更新失敗：{e}")


# =====================
# ENTRY POINT
# =====================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    show_login()
else:
    show_app()
