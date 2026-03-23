import streamlit as st
import xai_sdk
import asyncio
import base64
import requests
import json
from PIL import Image
import io

# 1. Konfiguracja strony
st.set_page_config(page_title="RAWMOTION Studio PRO", layout="wide", page_icon="🎬")

# 2. Bezpieczne pobieranie klucza
try:
    api_key = st.secrets["XAI_API_KEY"]
except Exception:
    st.error("❌ BŁĄD: Nie znaleziono klucza 'XAI_API_KEY' w Secrets!")
    st.stop()

# --- FUNKCJE LOGICZNE ---

def detect_aspect_ratio(image_bytes):
    """Automatycznie dobiera najlepsze ratio dla xAI na podstawie wymiarów zdjęcia."""
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size
    ratio = width / height
    
    if ratio > 1.2:
        return "16:9"
    elif ratio < 0.8:
        return "9:16"
    else:
        return "1:1"

def get_translated_prompt(polish_text, api_key):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    system_instr = (
        "You are a technical director for Memphis video engine. "
        "Rules: 1. Spoken Polish text must be in [voice: polish] tags. "
        "2. Keep EXACT Polish words. 3. Use [motion] and [camera] tags. "
        "4. Output only final technical prompt."
    )
    payload = {
        "model": "grok-4-1-fast-non-reasoning",
        "messages": [{"role": "system", "content": system_instr}, {"role": "user", "content": polish_text}],
        "temperature": 0.3
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response.json()['choices'][0]['message']['content'] if response.status_code == 200 else f"Błąd: {response.status_code}"

def get_video(api_key, img_b64, prompt, duration, auto_ratio):
    async def _async_call():
        client = xai_sdk.AsyncClient(api_key=api_key)
        return await client.video.generate(
            model="grok-imagine-video",
            image_url=img_b64,
            prompt=prompt,
            duration=duration,
            aspect_ratio=auto_ratio # Tu wchodzi automat
        )
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_call())
    finally:
        loop.close()

# --- INTERFEJS ---

st.title("🎬 RAWMOTION Studio PRO (Auto-Scale)")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ Parametry")
    duration = st.slider("Długość (s):", 5, 15, 6)
    st.info("System automatycznie dobierze format (16:9, 9:16 lub 1:1) na podstawie wgranego zdjęcia.")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. Scenariusz")
    polish_input = st.text_area("Opisz scenę po polsku:", height=100)
    
    if st.button("🪄 Przygotuj techniczny prompt (AI)", use_container_width=True):
        if polish_input:
            with st.spinner("Grok-4-Fast składa scenariusz..."):
                st.session_state['final_prompt'] = get_translated_prompt(polish_input, api_key)
        else:
            st.warning("Wpisz opis!")

    final_prompt = st.text_area("Finalny Prompt (możesz edytować):", value=st.session_state.get('final_prompt', ""), height=150)
    
    st.subheader("2. Materiał źródłowy")
    uploaded_file = st.file_uploader("Wgraj zdjęcie:", type=['jpg', 'jpeg', 'png'])

with col2:
    st.subheader("3. Render i Wynik")
    
    if st.button("🚀 WYPAL WIDEO", use_container_width=True, type="primary"):
        if uploaded_file and final_prompt:
            with st.spinner("Analizuję wymiary i renderuję..."):
                try:
                    img_bytes = uploaded_file.getvalue()
                    
                    # AUTOMATYCZNE RATIO
                    detected_ratio = detect_aspect_ratio(img_bytes)
                    st.write(f"✨ Wykryty format zdjęcia: **{detected_ratio}**")
                    
                    b64_img = base64.b64encode(img_bytes).decode('utf-8')
                    full_img_url = f"data:image/jpeg;base64,{b64_img}"
                    
                    video_obj = get_video(api_key, full_img_url, final_prompt, duration, detected_ratio)
                    
                    video_res = requests.get(video_obj.url)
                    st.video(video_res.content)
                    st.download_button("💾 POBIERZ MP4", video_res.content, "video.mp4", "video/mp4", use_container_width=True)
                except Exception as e:
                    st.error(f"⚠️ Błąd: {str(e)}")
        else:
            st.error("Wgraj zdjęcie i przygotuj prompt!")
