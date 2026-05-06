import streamlit as st
from openai import OpenAI
from supabase import create_client
import uuid
import base64
from PIL import Image
from io import BytesIO

# =====================
# CONFIG
# =====================
SUPABASE_URL = "https://yeurbbmwcartkoimcfch.supabase.co/rest/v1/"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlldXJiYm13Y2FydGtvaW1jZmNoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgwMzIwNzksImV4cCI6MjA5MzYwODA3OX0.88iWmZB7GLKirJfX3hqOtN2y1nHgIHauOr22EGghzIs"
OPENAI_API_KEY = "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" 
bucket = supabase.storage.from_("fashion-images")

# =====================
# STYLE MAP
# =====================
styles = {
    "Minimal": "minimalist fashion editorial outfit",
    "Street": "streetwear fashion design",
    "Luxury": "high fashion runway look",
    "Sport": "athletic sportswear design"
}

# =====================
# UPLOAD TO SUPABASE
# =====================
def upload_image(image_bytes):
    file_name = f"{uuid.uuid4()}.png"

    bucket.upload(
        file_name,
        image_bytes,
        {"content-type": "image/png"}
    )

    return bucket.get_public_url(file_name)

# =====================
# IMAGE GENERATION
# =====================
def generate_image(prompt):

    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    img_b64 = result.data[0].b64_json
    return base64.b64decode(img_b64)

# =====================
# 🧠 VISION + THINKING (FIXED)
# =====================
def analyze_and_edit(image_url, user_prompt, style):

    response = client.responses.create(
        model="gpt-4o",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"""
You are a professional fashion designer AI.

Task:
Modify the outfit in the image based on user request.

Style: {style}

User request:
{user_prompt}

Rules:
- keep model pose
- only modify clothing, fabric, fashion style
- output a high-quality image generation prompt
"""
                    },
                    {
                        "type": "input_image",
                        "image_url": image_url   # ✅ FIXED
                    }
                ]
            }
        ]
    )

    return response.output_text

# =====================
# SAVE TO SUPABASE
# =====================
def save(email, prompt, style, url):

    supabase.table("designs").insert({
        "user_email": email,
        "prompt": prompt,
        "style": style,
        "image_url": url
    }).execute()

# =====================
# UI
# =====================
st.title("👗 AI Fashion Editor v9 (Stable Fix Version)")

email = st.text_input("User Email")

style = st.selectbox("Style", list(styles.keys()))
user_prompt = st.text_area("What do you want to modify?")

uploaded_file = st.file_uploader(
    "Upload reference image",
    type=["png", "jpg", "jpeg"]
)

image_url = None
image_bytes = None

# =====================
# HANDLE UPLOAD
# =====================
if uploaded_file:
    image_bytes = uploaded_file.getvalue()

    st.image(image_bytes, caption="Original Image")

    image_url = upload_image(image_bytes)

    st.success("Image uploaded to Supabase")

# =====================
# MODIFY FLOW
# =====================
if st.button("Modify Image"):

    if not image_url:
        st.error("Please upload image first")
        st.stop()

    # 🧠 STEP 1: ANALYZE IMAGE
    with st.spinner("AI analyzing image..."):
        final_prompt = analyze_and_edit(
            image_url,
            user_prompt,
            styles[style]
        )

    st.subheader("🧠 Generated Prompt")
    st.write(final_prompt)

    # 🎨 STEP 2: GENERATE IMAGE
    with st.spinner("Generating new image..."):
        img_bytes = generate_image(final_prompt)

    st.image(img_bytes, caption="Edited Result")

    # ☁️ upload result
    result_url = upload_image(img_bytes)

    # 💾 save DB
    save(email, final_prompt, style, result_url)

    st.success("Done")