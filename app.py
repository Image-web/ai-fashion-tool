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
# STYLE PRESETS
# =====================
STYLES = {
    "Classic White": {
        "icon": "🤍",
        "desc": "乾淨俐落的商品白底攝影",
        "prompt": "professional product photography, pure white background, soft studio lighting, clean minimal fashion editorial, high-end commercial"
    },
    "Editorial": {
        "icon": "📸",
        "desc": "雜誌級時尚大片風格",
        "prompt": "high fashion editorial photography, dramatic lighting, Vogue magazine aesthetic, artistic composition, professional model shoot"
    },
    "Lifestyle": {
        "icon": "☀️",
        "desc": "自然生活感穿搭情境",
        "prompt": "lifestyle fashion photography, natural daylight, authentic candid feel, modern urban setting, approachable styling"
    },
    "Luxury": {
        "icon": "✨",
        "desc": "高端奢華品牌質感",
        "prompt": "luxury fashion brand photography, sophisticated lighting, premium quality, high-end retail aesthetic, elegant composition"
    },
    "Streetwear": {
        "icon": "🏙️",
        "desc": "都市街頭潮流風格",
        "prompt": "urban streetwear fashion photography, city backdrop, dynamic pose, contemporary street style, bold composition"
    },
    "Social Media": {
        "icon": "📱",
        "desc": "社群媒體吸睛版型",
        "prompt": "social media fashion content, bright and engaging, Instagram-worthy composition, trendy aesthetics, eye-catching colors"
    }
}

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

def build_prompt(user_input, style_key):
    """Combine user input with style preset"""
    style_prompt = STYLES[style_key]["prompt"]
    return f"{style_prompt}, {user_input}, ultra detailed, 8k quality"

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

        nav = st.radio("Navigation", ["✦ 生成圖片", "🖼 作品圖庫", "📋 我的紀錄"], label_visibility="collapsed")

        st.markdown("---")

        if st.button("登出"):
            for key in ["authenticated", "user", "email"]:
                st.session_state.pop(key, None)
            st.rerun()

    # --- MAIN CONTENT ---
    if "✦ 生成圖片" in nav:
        show_generate(email, usage, daily_limit)
    elif "🖼 作品圖庫" in nav:
        show_gallery()
    elif "📋 我的紀錄" in nav:
        show_history(email)


def show_generate(email, usage, daily_limit):
    st.markdown('<p class="main-title">設計工作室</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">AI 服裝形象圖生成</p>', unsafe_allow_html=True)

    if usage >= daily_limit:
        st.error(f"您今日已達 {daily_limit} 張上限，請明日再試")
        return

    col1, col2 = st.columns([1.1, 1], gap="large")

    with col1:
        st.markdown("#### 風格選擇")

        # Style picker as grid
        style_cols = st.columns(3)
        selected_style = st.session_state.get("selected_style", "Classic White")

        for i, (style_name, style_info) in enumerate(STYLES.items()):
            with style_cols[i % 3]:
                is_selected = style_name == selected_style
                border = "2px solid #1a1a1a" if is_selected else "1px solid #E0DDD8"
                bg = "#1a1a1a" if is_selected else "white"
                fg = "white" if is_selected else "#1a1a1a"

                if st.button(
                    f"{style_info['icon']} {style_name}",
                    key=f"style_{style_name}",
                    help=style_info["desc"]
                ):
                    st.session_state["selected_style"] = style_name
                    st.rerun()

        st.markdown("---")

        quality_key = st.selectbox(
            "畫質／模型",
            list(QUALITY_MODES.keys()),
            help="選擇生圖品質與模型。Ultra 會自動嘗試最新模型，不支援時自動降級。"
        )
        st.caption(f"　{QUALITY_MODES[quality_key]['desc']}")

        # 長寬比選擇
        ratio_key = st.selectbox(
            "長寬比",
            list(ASPECT_RATIOS.keys()),
            help="選擇圖片的長寬比例"
        )
        st.caption(f"　{ASPECT_RATIOS[ratio_key]['desc']}")

        # 解析度選擇
        res_key = st.selectbox(
            "解析度",
            list(RESOLUTION_TIERS.keys()),
            index=1,  # 預設 1K
            help="2K/4K 需要 gpt-image-2 帳號驗證，且屬於實驗性功能"
        )
        res_info = RESOLUTION_TIERS[res_key]
        if res_info["experimental"]:
            st.caption(f"　⚠️ {res_info['desc']}")
        else:
            st.caption(f"　{res_info['desc']}")

        user_prompt = st.text_area(
            "設計描述",
            placeholder="例如：流線型白色中長洋裝，搭配細緻花卉刺繡，優雅女性風格...",
            height=100
        )

        reference_file = st.file_uploader(
            "參考圖片（選填，用於圖片修改）",
            type=["png", "jpg", "jpeg"]
        )

        if reference_file:
            st.image(reference_file, caption="參考圖", use_container_width=True)

    with col2:
        st.markdown("#### 已選風格")
        sel = st.session_state.get("selected_style", "Classic White")
        st.markdown(f"""
        <div style="background:white;border:1px solid #E0DDD8;padding:1.5rem;margin-bottom:1rem;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">{STYLES[sel]['icon']}</div>
            <div style="font-family:'Cormorant Garamond',serif;font-size:1.3rem;font-weight:300;">{sel}</div>
            <div style="font-size:0.8rem;color:#888;margin-top:0.3rem;">{STYLES[sel]['desc']}</div>
        </div>
        """, unsafe_allow_html=True)

        # 右側輸出設定總覽
        qmode = QUALITY_MODES.get(quality_key, {})
        models_str = " → ".join(qmode.get("generate_models", []))
        img_quality = qmode.get("quality")
        quality_label = {"high": "🔴 高清 High", "medium": "🟡 標準 Medium", "low": "🟢 快速 Low"}.get(img_quality, "—")
        first_model = qmode.get("generate_models", ["dall-e-3"])[0]
        preview_size = get_size_for_model(first_model, ratio_key, res_key)
        pw, ph = preview_size.split("x")
        orient = "橫式" if int(pw) > int(ph) else ("直式" if int(ph) > int(pw) else "正方形")
        ratio_icon = ASPECT_RATIOS[ratio_key]["label"]
        res_info_disp = RESOLUTION_TIERS[res_key]
        exp_tag = " ⚠️ 實驗性" if res_info_disp["experimental"] else ""
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
        st.markdown(f'<p class="usage-counter">今日剩餘：{daily_limit - usage} 張</p>', unsafe_allow_html=True)

        # 數量選擇器
        num_images = st.selectbox(
            "生成數量",
            [1, 2, 3, 4, 5, 6, 8, 10],
            index=0,
            help="一次生成多張，每張獨立生成，佔用相同數量的每日額度"
        )

        remaining = daily_limit - usage
        if num_images > remaining:
            st.warning(f"今日剩餘 {remaining} 張，數量請調整為 {remaining} 以內")

        generate_btn = st.button("✦ 開始生成", use_container_width=True)

        if generate_btn:
            if not user_prompt.strip():
                st.warning("請描述您想生成的服裝設計")
            elif num_images > remaining:
                st.error(f"今日剩餘額度不足（剩 {remaining} 張），請減少數量")
            else:
                full_prompt = build_prompt(user_prompt, sel)

                st.markdown('<div class="prompt-box">' + full_prompt + '</div>', unsafe_allow_html=True)

                results = []  # 收集所有成功的結果

                for i in range(num_images):
                    label = f"第 {i+1} / {num_images} 張" if num_images > 1 else "生成中"
                    with st.spinner(f"AI 生成中：{label}，請稍候..."):
                        try:
                            if reference_file:
                                img_bytes = generate_image_from_reference(
                                    reference_file.getvalue(),
                                    full_prompt,
                                    quality_key,
                                    size_key
                                )
                            else:
                                img_bytes = generate_image_from_prompt(full_prompt, quality_key, size_key)

                            results.append(img_bytes)

                            # 上傳並儲存
                            url = upload_to_supabase(img_bytes)
                            save_design(email, full_prompt, sel, url)

                        except Exception as e:
                            st.error(f"第 {i+1} 張生成失敗：{e}")

                # 顯示所有結果
                if results:
                    st.success(f"✓ 成功生成 {len(results)} 張，已儲存至圖庫")

                    if len(results) == 1:
                        # 單張：全寬顯示
                        st.image(results[0], caption="生成結果", use_container_width=True)
                        st.download_button(
                            "⬇ 下載圖片",
                            data=results[0],
                            file_name=f"fashion_{sel.lower().replace(' ','_')}_{uuid.uuid4().hex[:6]}.png",
                            mime="image/png"
                        )
                    else:
                        # 多張：3欄 grid 顯示
                        cols = st.columns(3)
                        for idx, img_bytes in enumerate(results):
                            with cols[idx % 3]:
                                st.image(img_bytes, caption=f"第 {idx+1} 張", use_container_width=True)
                                st.download_button(
                                    f"⬇ 下載第 {idx+1} 張",
                                    data=img_bytes,
                                    file_name=f"fashion_{sel.lower().replace(' ','_')}_{idx+1}_{uuid.uuid4().hex[:6]}.png",
                                    mime="image/png",
                                    key=f"dl_{idx}"
                                )


def show_gallery():
    st.markdown('<p class="main-title">作品圖庫</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">全體員工作品</p>', unsafe_allow_html=True)

    col_search, col_filter = st.columns([2, 1])
    with col_search:
        search = st.text_input("搜尋", placeholder="搜尋描述或風格...")
    with col_filter:
        style_filter = st.selectbox("篩選風格", ["全部"] + list(STYLES.keys()))

    @st.cache_data(ttl=60)
    def load_gallery():
        return supabase.table("designs").select("*").order("created_at", desc=True).limit(100).execute()

    try:
        data = load_gallery()
        items = data.data or []
    except Exception as e:
        st.error(f"圖庫載入失敗：{e}")
        return

    # Filter
    if search:
        items = [i for i in items if search.lower() in (i.get("prompt", "") + i.get("style", "")).lower()]
    if style_filter != "全部":
        items = [i for i in items if i.get("style") == style_filter]

    valid_items = [i for i in items if i.get("image_url")]

    if not valid_items:
        st.info("尚無圖片")
        return

    st.markdown(f'<p style="font-size:0.8rem;color:#888;">{len(valid_items)} 張圖片</p>', unsafe_allow_html=True)

    cols = st.columns(3)
    for idx, item in enumerate(valid_items):
        with cols[idx % 3]:
            try:
                st.image(item["image_url"], use_container_width=True)
                style_icon = STYLES.get(item.get("style", ""), {}).get("icon", "")
                st.markdown(f'<span class="tag">{style_icon} {item.get("style","")}</span>', unsafe_allow_html=True)
                st.markdown(f'<p style="font-size:0.75rem;color:#888;margin-top:0.3rem;">{item.get("user_email","").split("@")[0]}</p>', unsafe_allow_html=True)
                st.markdown(f'<p style="font-size:0.8rem;color:#555;">{item.get("prompt","")[:80]}...</p>', unsafe_allow_html=True)
                st.markdown("---")
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
                st.markdown(f'<span class="tag">{item.get("style","")}</span>', unsafe_allow_html=True)
                created = item.get("created_at", "")[:10]
                st.markdown(f'<p style="font-size:0.75rem;color:#888;">{created}</p>', unsafe_allow_html=True)
                st.markdown("---")
            except:
                pass


# =====================
# ENTRY POINT
# =====================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    show_login()
else:
    show_app()
