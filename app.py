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
st.set_page_config(page_title="RAWMOTION Director v7.0", layout="wide", page_icon="🎬")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔐 Director's Entrance")
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
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    async def _async_gen():
        client = xai_sdk.AsyncClient(api_key=api_key)
        return await client.image.sample(model=model_name, prompt=prompt, aspect_ratio="1:1")
    try: return loop.run_until_complete(_async_gen())
    finally: loop.close()

def edit_image_xai(api_key, img_bytes, prompt, model_name="grok-imagine-image-pro"):
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    async def _async_edit():
        client = xai_sdk.AsyncClient(api_key=api_key)
        uri = f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode('utf-8')}"
        return await client.image.sample(model=model_name, prompt=prompt, image_url=uri)
    try: return loop.run_until_complete(_async_edit())
    finally: loop.close()

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v7.0 (The Final Studio)")

if "draft" not in st.session_state: st.session_state.draft = ""
if "active_ai_source" not in st.session_state: st.session_state.active_ai_source = None

# --- SIDEBAR: CENTRUM DOWODZENIA ---
with st.sidebar:
    mode = st.radio("🎬 Tryb Obsady:", ["Solo (1 Osoba / AI)", "Duo (2 Osoby - Konfrontacja)"])
    st.divider()

    if mode == "Solo (1 Osoba / AI)":
        st.subheader("👤 Zarządzanie Solo")
        up_file = st.file_uploader("Wgraj zdjęcie źródłowe:", type=['jpg','png','jpeg'])
        if up_file:
            char_desc = st.text_input("Opisz postać (PL):", "Fotorealistyczna kobieta")
            if st.button("➕ Wstaw [character]", use_container_width=True):
                st.session_state.draft += f"{elon_translator(char_desc, 'character')} "
        
        st.divider()
        st.subheader("✨ Generator AI")
        gen_p = st.text_input("Kogo stworzyć?")
        if st.button("🚀 Generuj AI", use_container_width=True):
            with st.spinner("Grok tworzy..."):
                res = generate_image_xai(api_key, gen_p)
                st.session_state.active_ai_source = Image.open(io.BytesIO(requests.get(res.url).content))
                st.session_state.draft += f"{elon_translator(gen_p, 'character')} "
        
        st.divider()
        st.subheader("🛠️ Tuning FX")
        if up_file or st.session_state.active_ai_source:
            edit_p = st.text_input("Zmiana (np. red dress):")
            if st.button("🪄 Wykonaj Tuning", use_container_width=True):
                with st.spinner("Edytuję..."):
                    src = up_file.getvalue() if up_file else None
                    if not src:
                        buf = io.BytesIO(); st.session_state.active_ai_source.save(buf, format="PNG"); src = buf.getvalue()
                    res = edit_image_xai(api_key, src, edit_p)
                    st.session_state.active_ai_source = Image.open(io.BytesIO(requests.get(res.url).content))
                    st.session_state.draft += f"[motion: transformation to {edit_p}] "

    else: # TRYB DUO
        st.subheader("👥 Duo Direct")
        up_a = st.file_uploader("Zdjęcie 1 (Osoba A):", type=['jpg','png','jpeg'])
        up_b = st.file_uploader("Zdjęcie 2 (Osoba B):", type=['jpg','png','jpeg'])
        if up_a:
            if st.button("➕ Wstaw Postać A", use_container_width=True):
                st.session_state.draft += "[character: Person A from Image 1] "
        if up_b:
            if st.button("➕ Wstaw Postać B", use_container_width=True):
                st.session_state.draft += "[character: Person B from Image 2] "

    st.divider()
    if st.button("⏪ UNDO (Cofnij)", use_container_width=True):
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1]); st.rerun()
    if st.button("🗑️ CZYŚĆ SCENARIUSZ", type="secondary", use_container_width=True):
        st.session_state.draft = ""; st.session_state.active_ai_source = None; st.rerun()

# --- PANEL REŻYSERSKI 3x2 ---
st.subheader("🖼️ Podgląd Materiału")
col_img, col_ui = st.columns([1, 2])
with col_img:
    if mode == "Solo (1 Osoba / AI)":
        disp = st.session_state.active_ai_source if st.session_state.active_ai_source else (Image.open(up_file) if up_file else None)
        if disp: st.image(disp, use_container_width=True)
    else:
        c1, c2 = st.columns(2)
        with c1: 
            if up_a: st.image(Image.open(up_a), caption="A", use_container_width=True)
        with c2: 
            if up_b: st.image(Image.open(up_b), caption="B", use_container_width=True)

with col_ui:
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.subheader("🎥 Kamera")
        cam_list = ["steady close-up — Portret", "tilt down to hips — Biodra", "full shot — Sylwetka", "dolly zoom in — Szok", "orbit shot — Krążenie", "dutch angle — Krzywy", "handheld shake — Realizm"]
        sel_cam = st.selectbox("Ujęcie:", cam_list)
        if st.button("➕ Kamera"): st.session_state.draft += f"[camera: {sel_cam.split(' — ')[0]}] "
    with r1c2:
        st.subheader("🎙️ Dialog")
        txt = st.text_input("Tekst mowy:")
        if st.button("➕ Dialog"): st.session_state.draft += f"[voice: polish] \"{txt}\" [pause: 0.5s] "
    with r1c3:
        st.subheader("💃 Ruch")
        act = st.text_input("Akcja (PL):")
        if st.button("➕ Ruch"): st.session_state.draft += f"{elon_translator(act, 'motion')} "

    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        st.subheader("🎵 Muzyka")
        m_opt = st.selectbox("Styl:", ["Hip-Hop", "Cinematic", "Lo-Fi", "Romantic", "Techno"])
        if st.button("➕ Audio"): st.session_state.draft += f"[audio: background {m_opt.lower()}] "
    with r2c2:
        st.subheader("🔊 SFX")
        s_opt = st.selectbox("Efekt:", ["Applause", "Heartbeat", "Thunder", "Shutter", "Scream"])
        if st.button("➕ SFX"): st.session_state.draft += f"[audio: {s_opt.lower()}] "
    with r2c3:
        st.subheader("🎭 Głos")
        v_opt = st.selectbox("Filtr:", ["Whisper", "Radio", "Echo", "Deep Bass", "Robot"])
        if st.button("➕ Filtr"): st.session_state.draft += f"[audio: {v_opt.lower()}] "

# --- RENDER ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=120)
dur = st.slider("Długość (s):", 5, 15, 10)

if st.button("🚀 WYPAL FINALNE WIDEO (HD)", type="primary", use_container_width=True):
    with st.spinner("Produkcja trwa..."):
        try:
            c = xai_sdk.AsyncClient(api_key=api_key)
            if mode == "Solo (1 Osoba / AI)":
                buf = io.BytesIO(); disp.save(buf, format="JPEG"); b64 = base64.b64encode(buf.getvalue()).decode()
                res = asyncio.run(c.video.generate(model="grok-imagine-video", image_url=f"data:image/jpeg;base64,{b64}", prompt=st.session_state.draft, duration=dur, resolution="720p"))
            else:
                b64_a = base64.b64encode(up_a.getvalue()).decode()
                b64_b = base64.b64encode(up_b.getvalue()).decode()
                res = asyncio.run(c.video.generate(model="grok-imagine-video", image_url=[f"data:image/jpeg;base64,{b64_a}", f"data:image/jpeg;base64,{b64_b}"], prompt=st.session_state.draft, duration=dur, resolution="720p"))
            st.video(requests.get(res.url).content)
        except Exception as e: st.error(f"Błąd: {e}")
