import streamlit as st
import xai_sdk
import asyncio
import base64
import requests
import json
from PIL import Image
import io
import re

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION Director's Cut", layout="wide", page_icon="🎬")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔐 Director's Entrance")
        try:
            correct_password = st.secrets["MY_APP_PASSWORD"]
        except:
            st.error("Ustaw MY_APP_PASSWORD w Secrets!")
            st.stop()
        pwd = st.text_input("Hasło:", type="password")
        if st.button("Wejdź"):
            if pwd == correct_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Błędne hasło.")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. LOGIC & HELPERS ---
try:
    api_key = st.secrets["XAI_API_KEY"]
except:
    st.error("Brak XAI_API_KEY!")
    st.stop()

def estimate_duration(prompt):
    # Liczenie pauz: szuka [pause: Xs]
    pauses = re.findall(r"\[pause:\s*(\d+\.?\d*)s\]", prompt)
    pause_time = sum(float(p) for p in pauses)
    # Liczenie słów (pomijając tagi w [])
    clean_text = re.sub(r"\[.*?\]", "", prompt)
    words = len(clean_text.split())
    speech_time = words * 0.65 # średnio 0.65s na polskie słowo
    total = pause_time + speech_time + 2.5 # +2.5s na kamerę/akcję
    return round(total, 1)

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

# --- 3. THE BUILDER INTERFACE ---
st.title("🎬 RAWMOTION Director's Cut v2.0")

if "draft" not in st.session_state:
    st.session_state.draft = ""

# Sidebar: Globalne ustawienia postaci
with st.sidebar:
    st.header("👤 Definicja Postaci")
    char_global = st.text_area("Opisz postać (raz a dobrze):", 
                              value="Fotorealistyczna kobieta ze zdjęcia, styl kinowy, naturalna cera",
                              help="To zostanie wstawione po kliknięciu klocka [POSTAĆ]")
    st.divider()
    st.info("💡 Klikaj klocki poniżej, aby budować oś czasu filmu.")

# GŁÓWNY PANEL KLOCKÓW
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("**🧱 FUNDAMENTY**")
    if st.button("👤 Dodaj POSTAĆ"):
        st.session_state.draft += f"[motion: {char_global}] "
    if st.button("🇵🇱 GŁOS (PL)"):
        st.session_state.draft += "[voice: polish] "

with c2:
    st.markdown("**🎥 KAMERA**")
    if st.button("🔭 Zoom Twarz (Steady)"):
        st.session_state.draft += "[camera: steady close-up on face, high-fidelity facial animation] "
    if st.button("📉 Zjazd na Biodra"):
        st.session_state.draft += "[camera: dynamic tilt down to hips, handheld shake] "
    if st.button("🫨 Kamera z Ręki"):
        st.session_state.draft += "[camera: handheld shake] "

with c3:
    st.markdown("**💃 AKCJA / FX**")
    if st.button("👄 Perfect Lip-Sync"):
        st.session_state.draft += "[motion: perfect lip-sync] "
    if st.button("🍑 Ruch Bioder"):
        st.session_state.draft += "[motion: swaying hips seductively, circular hip movement] "
    if st.button("😉 Mrugnięcie"):
        st.session_state.draft += "[motion: playful wink and smile] "

with c4:
    st.markdown("**⏱️ CZAS / PAUZY**")
    if st.button("⏸️ Pauza 0.5s"):
        st.session_state.draft += "[pause: 0.5s] "
    if st.button("⏳ Pauza 1.0s"):
        st.session_state.draft += "[pause: 1.0s] "
    if st.button("🗑️ CZYŚĆ DRAFT", type="secondary"):
        st.session_state.draft = ""
        st.rerun()

# EDYTOR SCENARIUSZA
st.divider()
final_prompt = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=200)
st.session_state.draft = final_prompt # Synchronizacja edycji ręcznej

# ESTYMATOR
if final_prompt:
    est_time = estimate_duration(final_prompt)
    est_cost = round(est_time * 0.05, 2) # Szacunkowo 5 centów za sekundę
    st.success(f"⏱️ Szacowany czas: **{est_time}s** | 💰 Przybliżony koszt: **${est_cost}**")

# PANEL RENDEROWANIA
st.divider()
col_ren1, col_ren2 = st.columns([1, 1])

with col_ren1:
    uploaded_file = st.file_uploader("🖼️ Wgraj zdjęcie źródłowe:", type=['jpg','png','jpeg'])
    duration_slider = st.slider("Ustaw długość renderu (s):", 5, 15, int(min(max(est_time if final_prompt else 6, 5), 15)))

with col_ren2:
    if st.button("🚀 WYPAL WIDEO (GENERATE)", type="primary", use_container_width=True):
        if uploaded_file and final_prompt:
            with st.spinner("Reżyseruję klatki..."):
                try:
                    img_bytes = uploaded_file.getvalue()
                    img = Image.open(io.BytesIO(img_bytes))
                    w, h = img.size
                    ratio = "16:9" if w/h > 1.2 else "9:16" if w/h < 0.8 else "1:1"
                    
                    b64 = base64.b64encode(img_bytes).decode()
                    video = get_video(api_key, f"data:image/jpeg;base64,{b64}", final_prompt, duration_slider, ratio)
                    
                    v_data = requests.get(video.url).content
                    st.video(v_data)
                    st.download_button("💾 POBIERZ KLIP", v_data, "rawmotion_clip.mp4", "video/mp4")
                except Exception as e:
                    st.error(f"⚠️ Błąd: {str(e)}")
        else:
            st.error("Brakuje zdjęcia lub scenariusza!")
