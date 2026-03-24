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
st.set_page_config(page_title="RAWMOTION Master Director v6.0", layout="wide", page_icon="🎬")

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

def fuse_images_xai(api_key, img_a_bytes, img_b_bytes, prompt, model_name="grok-imagine-image-pro"):
    url = "https://api.x.ai/v1/images/edits"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # Upewniamy się, że format to JPEG dla mniejszej wagi transferu
    uri_a = f"data:image/jpeg;base64,{base64.b64encode(img_a_bytes).decode('utf-8')}"
    uri_b = f"data:image/jpeg;base64,{base64.b64encode(img_b_bytes).decode('utf-8')}"
    
    payload = {
        "model": model_name,
        "images": [uri_a, uri_b],
        "prompt": prompt,
        "aspect_ratio": "16:9"
    }
    
    res = requests.post(url, headers=headers, json=payload, timeout=120)
    
    if res.status_code == 200:
        return res.json()['data'][0]['url']
    elif res.status_code == 400:
        # Jeśli to błąd moderacji lub twarzy
        raise Exception(f"xAI odrzuciło zdjęcia (prawdopodobnie filtry rozpoznawania twarzy osób publicznych).")
    else:
        raise Exception(f"Błąd API {res.status_code}: {res.text}")

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Master Director v6.0")

if "draft" not in st.session_state: st.session_state.draft = ""
if "active_source" not in st.session_state: st.session_state.active_source = None

# --- SIDEBAR: CENTRUM DOWODZENIA ---
with st.sidebar:
    st.header("🕹️ Tryb Pracy")
    mode = st.radio("Wybierz obsadę:", ["Solo (1 osoba / Generator)", "Duo (Fuzja 2 osób)"], index=0)
    
    st.divider()
    
    if mode == "Solo (1 osoba / Generator)":
        st.subheader("👤 Zarządzanie Postacią")
        up_file = st.file_uploader("Wgraj zdjęcie źródłowe:", type=['jpg','png','jpeg'])
        if up_file:
            desc_pl = st.text_input("Opisz postać (PL):", "Fotorealistyczna postać")
            if st.button("➕ Wstaw [character] do Osi", use_container_width=True):
                st.session_state.draft += f"{elon_translator(desc_pl, 'character')} "
        
        st.divider()
        st.subheader("✨ Generator AI (Od zera)")
        gen_p = st.text_input("Kogo stworzyć? (ang/pl):")
        if st.button("🚀 Generuj i Wstaw AI", use_container_width=True):
            with st.spinner("Grok tworzy..."):
                res = generate_image_xai(api_key, gen_p)
                st.session_state.active_source = Image.open(io.BytesIO(requests.get(res.url).content))
                st.session_state.draft += f"{elon_translator(gen_p, 'character')} "
        
        st.divider()
        st.subheader("🛠️ Tuning FX (Edycja)")
        if up_file or st.session_state.active_source:
            edit_p = st.text_input("Zmiana (np. green dress):")
            if st.button("🪄 Wykonaj Tuning", use_container_width=True):
                with st.spinner("Tuning..."):
                    src = up_file.getvalue() if up_file else None
                    if not src:
                        buf = io.BytesIO(); st.session_state.active_source.save(buf, format="PNG"); src = buf.getvalue()
                    res = edit_image_xai(api_key, src, edit_p)
                    st.session_state.active_source = Image.open(io.BytesIO(requests.get(res.url).content))
                    st.session_state.draft += f"[motion: transformation to {edit_p}] "

    else: # TRYB DUO
        st.subheader("👥 Fuzja Duo")
        up_a = st.file_uploader("Osoba A:", type=['jpg','png','jpeg'])
        up_b = st.file_uploader("Osoba B:", type=['jpg','png','jpeg'])
        if up_a and up_b:
            fuse_p = st.text_input("Opisz ich wspólną scenę (PL):", placeholder="rozmawiają na plaży...")
            if st.button("🪄 Wykonaj Fuzję Duo-FX", use_container_width=True):
                with st.spinner("Grok łączy postacie..."):
                    res_url = fuse_images_xai(api_key, up_a.getvalue(), up_b.getvalue(), elon_translator(fuse_p, "action"))
                    st.session_state.active_source = Image.open(io.BytesIO(requests.get(res_url).content))
                    st.session_state.draft += f"[motion: high-fidelity duo interaction {fuse_p}] "

    st.divider()
    if st.button("⏪ UNDO", use_container_width=True):
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1]); st.rerun()
    if st.button("🗑️ CZYŚĆ", type="secondary", use_container_width=True):
        st.session_state.draft = ""; st.session_state.active_source = None; st.rerun()

# --- PANEL REŻYSERSKI 3x2 ---
st.subheader("🖼️ Podgląd Materiału")
col_img, col_ui = st.columns([1, 2])
with col_img:
    # Logika wyświetlania podglądu
    disp_img = st.session_state.active_source
    if not disp_img and mode == "Solo (1 osoba / Generator)" and "up_file" in locals() and up_file:
        disp_img = Image.open(up_file)
    if disp_img: st.image(disp_img, use_container_width=True)
    else: st.info("Wgraj zdjęcie lub wygeneruj postać.")

with col_ui:
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.subheader("🎥 Kamera")
        cam_list = ["steady close-up on face — Portret", "dynamic tilt down to hips — Biodra", "full shot — Sylwetka", "dolly zoom in — Szok", "handheld shake — Realizm", "orbit shot — Kamera krąży", "dutch angle — Krzywy kadr"]
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
        m_opt = st.selectbox("Podkład:", ["Subtle Hip-Hop", "Cinematic Tension", "Lo-Fi Chill", "Romantic Piano", "Dark Techno"])
        if st.button("➕ Audio"): st.session_state.draft += f"[audio: background {m_opt.lower()}] "
    with r2c2:
        st.subheader("🔊 SFX")
        s_opt = st.selectbox("Efekt:", ["Crowd Applause", "Heavy Breathing", "Heartbeat Thump", "Thunder Clap", "Camera Shutter"])
        if st.button("➕ SFX"): st.session_state.draft += f"[audio: {s_opt.lower()}] "
    with r2c3:
        st.subheader("🎭 Głos")
        v_opt = st.selectbox("Filtr:", ["Whisper", "Radio Filter", "Echo Reverb", "Robot Voice", "Deep Bass"])
        if st.button("➕ Filtr"): st.session_state.draft += f"[audio: {v_opt.lower()}] "

# --- RENDER ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=120)
dur = st.slider("Długość (s):", 5, 15, 10)
if st.button("🚀 WYPAL FINALNE WIDEO (HD)", type="primary", use_container_width=True):
    if disp_img and st.session_state.draft:
        with st.spinner("Renderowanie 720p..."):
            buf = io.BytesIO(); disp_img.save(buf, format="JPEG"); b64 = base64.b64encode(buf.getvalue()).decode()
            async def _gen():
                c = xai_sdk.AsyncClient(api_key=api_key)
                return await c.video.generate(model="grok-imagine-video", image_url=f"data:image/jpeg;base64,{b64}", prompt=st.session_state.draft, duration=dur, resolution="720p")
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); video = loop.run_until_complete(_gen())
            st.video(requests.get(video.url).content)
