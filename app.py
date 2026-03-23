import streamlit as st
import xai_sdk
import asyncio
import base64
import requests
import json
from PIL import Image
import io

# --- 1. KONFIGURACJA I ZABEZPIECZENIE ---
st.set_page_config(page_title="RAWMOTION Ultra Studio", layout="wide", page_icon="🎥")

# Zamiast APP_PASSWORD = "Wojtek"
APP_PASSWORD = st.secrets["MY_APP_PASSWORD"]

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.title("🔐 Autoryzacja Studia")
        pwd = st.text_input("Podaj hasło dostępowe:", type="password")
        if st.button("Wejdź"):
            if pwd == APP_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Nieprawidłowe hasło!")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. LOGIKA API ---
try:
    api_key = st.secrets["XAI_API_KEY"]
except:
    st.error("Brak API KEY w Secrets!")
    st.stop()

def get_video(api_key, img_b64, prompt, duration, ratio):
    async def _async_call():
        client = xai_sdk.AsyncClient(api_key=api_key)
        return await client.video.generate(
            model="grok-imagine-video",
            image_url=img_b64,
            prompt=prompt,
            duration=duration,
            aspect_ratio=ratio
        )
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: return loop.run_until_complete(_async_call())
    finally: loop.close()

# --- 3. INTERFEJS ULTRA STUDIO ---
st.title("🎥 RAWMOTION Ultra Studio")
st.caption(f"Zalogowano jako: PhilBackensky | Silnik: Memphis & Grok-4-Fast")

tab1, tab2, tab3 = st.tabs(["👥 Reżyseria Postaci", "🎥 Kamera & Styl", "🎬 Render"])

with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Osoba 1 (Lewo/Główna)")
        char1_desc = st.text_input("Opis wyglądu (np. blondynka w czerwonym):", key="c1_d")
        char1_action = st.text_area("Co robi / mówi:", placeholder="Mówi: 'Cześć!', mruga okiem...", key="c1_a")
        
    with col_b:
        st.subheader("Osoba 2 (Prawo/Tło)")
        char2_desc = st.text_input("Opis wyglądu (np. facet w okularach):", key="c2_d")
        char2_action = st.text_area("Co robi / mówi:", placeholder="Śmieje się, klaszcze...", key="c2_a")

    st.divider()
    st.subheader("🪄 Efekty Audio/Video (Kliknij, aby dodać do akcji)")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("⏳ Dodaj Pauzę (1s)"): st.info("Wklej manualnie: [pause: 1s]")
    if c2.button("🔊 Podgłośnij"): st.info("Wklej manualnie: [volume: +5db]")
    if c3.button("😉 Mrugnięcie"): st.info("Wklej manualnie: [motion: wink]")
    if c4.button("🔥 Emocje++"): st.info("Wklej manualnie: [expression: intense]")

with tab2:
    st.subheader("Ustawienia Kamery")
    cam_move = st.selectbox("Ruch kamery:", ["static", "zoom in", "dolly zoom", "handheld shake", "pan left", "pan right"])
    video_style = st.selectbox("Stylistyka:", ["Photorealistic", "Cinematic 35mm", "VHS Retro", "Cyberpunk Neon", "Film Noir (B&W)"])
    duration = st.slider("Długość (sekundy):", 5, 15, 6)

with tab3:
    uploaded_file = st.file_uploader("Wgraj zdjęcie źródłowe:", type=['jpg','png','jpeg'])
    
    if st.button("🧪 GENERUJ PROMPT TECHNICZNY", use_container_width=True):
        # Tutaj logika sklejania warstw przez Groka (uproszczona dla stabilności)
        raw_story = f"Style: {video_style}. Camera: {cam_move}. Character 1 ({char1_desc}): {char1_action}. Character 2 ({char2_desc}): {char2_action}."
        
        url = "https://api.x.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
        "model": "grok-4-1-fast-non-reasoning",
        "messages": [
            {
                "role": "system", 
                "content": (
                    "You are a professional technical director for Memphis video engine. "
                    "STRICT RULES: 1. Spoken Polish text MUST be inside [voice: polish] tags. "
                    "2. NEVER use closing tags like [/voice] or [/motion]. "
                    "3. ALWAYS start prompts with: [motion: high-fidelity facial animation, perfect lip-sync]. "
                    "4. Automatically insert [pause: 0.5s] at the start of speech and between sentences. "
                    "5. Keep camera settings at the very beginning."
                )
            },
            {"role": "user", "content": raw_story}
        ],
        "temperature": 0.3
    }
        res = requests.post(url, headers=headers, json=payload)
        st.session_state["ultra_prompt"] = res.json()['choices'][0]['message']['content']

    final_p = st.text_area("Finalny Scenariusz:", value=st.session_state.get("ultra_prompt", ""), height=150)
    
    if st.button("🚀 WYPAL WIDEO (PRODUKCJA)", type="primary", use_container_width=True):
        if uploaded_file and final_p:
            with st.spinner("Produkcja w toku..."):
                img_bytes = uploaded_file.getvalue()
                img = Image.open(io.BytesIO(img_bytes))
                w, h = img.size
                ratio = "16:9" if w/h > 1.2 else "9:16" if w/h < 0.8 else "1:1"
                
                b64 = base64.b64encode(img_bytes).decode()
                video = get_video(api_key, f"data:image/jpeg;base64,{b64}", final_p, duration, ratio)
                
                v_data = requests.get(video.url).content
                st.video(v_data)
                st.download_button("💾 POBIERZ MP4", v_data, "render.mp4", "video/mp4")
