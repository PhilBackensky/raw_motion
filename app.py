import streamlit as st
import xai_sdk
import asyncio
import base64
import requests
import json
from PIL import Image
import io
import re
from datetime import timedelta

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION Director v5.7", layout="wide", page_icon="🎬")

# --- CUSTOM CSS DLA SMARTFONÓW ---
st.markdown("""
    <style>
    /* Wymuszenie siatki dla kolumn na mobilkach */
    @media (max-width: 768px) {
        [data-testid="column"] {
            width: 48% !important;
            flex: 1 1 48% !important;
            min-width: 48% !important;
            display: inline-block !important;
        }
        div[data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: wrap !important;
        }
        /* Zmniejszenie odstępów, żeby więcej weszło na ekran */
        .stButton button {
            width: 100% !important;
            padding: 0.2rem !important;
            font-size: 12px !important;
        }
        h3 {
            font-size: 16px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔐 Entrance")
        try: correct_password = st.secrets["MY_APP_PASSWORD"]
        except: st.error("Błąd Secrets!"); st.stop()
        pwd = st.text_input("Hasło:", type="password")
        if st.button("Wejdź"):
            if pwd == correct_password: st.session_state["authenticated"] = True; st.rerun()
            else: st.error("Błędne hasło.")
        return False
    return True

if not check_password(): st.stop()

# --- 2. LOGIC & API ---
api_key = st.secrets["XAI_API_KEY"]

def elon_translator(text, context_type):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    tag_format = "[character: ...]" if context_type == "character" else "[motion: ...]"
    prompt = f"Translate to technical tag for Memphis engine using {tag_format}. Output ONLY tag. Text: {text}"
    payload = {"model": "grok-4-1-fast-non-reasoning", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    try:
        res = requests.post(url, headers=headers, json=payload)
        return res.json()['choices'][0]['message']['content']
    except: return f"[{context_type}: error]"

def generate_image_xai(api_key, prompt, model_name="grok-imagine-image-pro"):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def _async_gen():
        client = xai_sdk.AsyncClient(api_key=api_key)
        return await client.image.sample(model=model_name, prompt=prompt, aspect_ratio="1:1")
    try: return loop.run_until_complete(_async_gen())
    finally: loop.close()

def edit_image_xai(api_key, img_bytes, prompt, model_name="grok-imagine-image-pro"):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def _async_edit():
        client = xai_sdk.AsyncClient(api_key=api_key)
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        data_uri = f"data:image/png;base64,{img_b64}"
        return await client.image.sample(model=model_name, prompt=prompt, image_url=data_uri)
    try: return loop.run_until_complete(_async_edit())
    finally: loop.close()

def estimate_duration(prompt):
    words = len(re.sub(r"\[.*?\]", "", prompt).split())
    return round(words * 0.8 + 4.0, 1)

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v5.7")

if "draft" not in st.session_state: st.session_state.draft = ""
if "active_ai_image" not in st.session_state: st.session_state.active_ai_image = None

uploaded_file = st.file_uploader("🖼️ KROK 1: Zdjęcie źródłowe:", type=['jpg','png','jpeg'])

# --- SIDEBAR (Mobilny) ---
with st.sidebar:
    st.header("👤 Postać")
    tab_gen, tab_edit = st.tabs(["✨ Generator", "🖼️ FX"])
    
    with tab_gen:
        gen_prompt = st.text_area("Kogo stworzyć?", placeholder="Ana de Armas...")
        if st.button("🚀 Generuj AI", use_container_width=True):
            with st.spinner("Tworzę..."):
                res = generate_image_xai(api_key, gen_prompt)
                st.session_state.active_ai_image = Image.open(io.BytesIO(requests.get(res.url).content))
    
    with tab_edit:
        if uploaded_file or st.session_state.active_ai_image:
            edit_p = st.text_input("Zmiana (np. red dress):")
            if st.button("🪄 Tunuj FX", use_container_width=True):
                with st.spinner("FX..."):
                    source = uploaded_file.getvalue() if uploaded_file else None
                    if not source:
                        buf = io.BytesIO(); st.session_state.active_ai_image.save(buf, format="PNG"); source = buf.getvalue()
                    res = edit_image_xai(api_key, source, edit_p)
                    st.session_state.active_ai_image = Image.open(io.BytesIO(requests.get(res.url).content))
                    st.session_state.draft += f"[motion: transformation to {edit_p}] "

    st.divider()
    if st.button("⏪ UNDO", use_container_width=True):
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1]); st.rerun()
    if st.button("🗑️ CZYŚĆ", type="secondary", use_container_width=True):
        st.session_state.draft = ""; st.rerun()

# --- PANEL REŻYSERSKI (RESPONSYWNY) ---
st.divider()
col_img, col_ui = st.columns([1, 2])
with col_img:
    img_to_show = st.session_state.active_ai_image if st.session_state.active_ai_image else (Image.open(uploaded_file) if uploaded_file else None)
    if img_to_show: st.image(img_to_show, use_container_width=True)

with col_ui:
    r1c1, r1c2 = st.columns(2) # Na mobilkach będą obok siebie
    with r1c1:
        st.subheader("🎥 Kamera")
        cam = st.selectbox("Ujęcie:", ["Portret", "Biodra", "Sylwetka", "Szok", "Vertigo", "Realizm"], label_visibility="collapsed")
        if st.button("➕ Kamera"):
            tags = {"Portret": "steady close-up on face", "Biodra": "tilt down to hips", "Sylwetka": "full shot", "Szok": "dolly zoom in", "Vertigo": "orbit shot", "Realizm": "handheld shake"}
            st.session_state.draft += f"[camera: {tags[cam]}] "

    with r1c2:
        st.subheader("💃 Ruch")
        act = st.text_input("Akcja:", placeholder="uśmiech...", label_visibility="collapsed")
        if st.button("➕ Ruch"):
            st.session_state.draft += f"{elon_translator(act, 'motion')} "

    st.divider()
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        st.subheader("🎙️ Dialog")
        txt = st.text_input("Tekst:", placeholder="Mów...", label_visibility="collapsed")
        if st.button("➕ Dialog"):
            st.session_state.draft += f"[voice: polish] \"{txt}\" "

    with r2c2:
        st.subheader("🎵 Audio")
        aud = st.selectbox("Styl:", ["Hip-Hop", "Tension", "Lo-Fi", "Piano", "Techno"], label_visibility="collapsed")
        if st.button("➕ Audio"):
            st.session_state.draft += f"[audio: background {aud.lower()}] "

# --- RENDER ---
st.divider()
st.session_state.draft = st.text_area("🛠️ DRAFT:", value=st.session_state.draft, height=100)
dur = st.slider("Czas (s):", 5, 15, 10)

if st.button("🚀 WYPAL WIDEO", type="primary", use_container_width=True):
    img = img_to_show
    if img and st.session_state.draft:
        with st.spinner("Render..."):
            buf = io.BytesIO(); img.save(buf, format="JPEG"); b64 = base64.b64encode(buf.getvalue()).decode()
            async def _gen():
                c = xai_sdk.AsyncClient(api_key=api_key)
                return await c.video.generate(model="grok-imagine-video", image_url=f"data:image/jpeg;base64,{b64}", prompt=st.session_state.draft, duration=dur, resolution="720p")
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); video = loop.run_until_complete(_gen())
            st.video(requests.get(video.url).content)
