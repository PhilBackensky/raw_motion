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
st.set_page_config(page_title="RAWMOTION Director v7.2", layout="wide", page_icon="🎬")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔐 Director's Entrance")
        try:
            correct_password = st.secrets["MY_APP_PASSWORD"]
        except:
            st.error("Błąd: Brak MY_APP_PASSWORD w Secrets!")
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
    except:
        return f"[{context_type}: error]"

# Funkcja pomocnicza do obsługi asynchronicznych wywołań w Streamlit
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v7.2")

if "draft" not in st.session_state: st.session_state.draft = ""
if "active_ai_source" not in st.session_state: st.session_state.active_ai_source = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Studio Setup")
    mode = st.radio("Tryb Obsady:", ["Solo (1 Osoba / AI)", "Duo (2 Osoby - Direct)"])
    st.divider()

    if mode == "Solo (1 Osoba / AI)":
        st.subheader("👤 Zarządzanie Solo")
        up_file = st.file_uploader("Wgraj zdjęcie:", type=['jpg','png','jpeg'])
        if up_file:
            char_desc = st.text_input("Opisz postać (PL):", "Fotorealistyczna postać")
            if st.button("➕ Wstaw [character]", use_container_width=True):
                st.session_state.draft += f"{elon_translator(char_desc, 'character')} "
        
        st.divider()
        st.subheader("✨ Generator AI")
        gen_p = st.text_input("Kogo stworzyć?")
        if st.button("🚀 Generuj AI", use_container_width=True):
            with st.spinner("Grok tworzy obraz..."):
                client = xai_sdk.Client(api_key=api_key)
                res = client.image.sample(model="grok-imagine-image-pro", prompt=gen_p, aspect_ratio="1:1")
                st.session_state.active_ai_source = Image.open(io.BytesIO(requests.get(res.url).content))
                st.session_state.draft += f"{elon_translator(gen_p, 'character')} "
        
        st.divider()
        st.subheader("🛠️ Tuning FX")
        if up_file or st.session_state.active_ai_source:
            edit_p = st.text_input("Zmiana (np. niebieska sukienka):")
            if st.button("🪄 Wykonaj Tuning", use_container_width=True):
                with st.spinner("Edytuję..."):
                    src_bytes = up_file.getvalue() if up_file else None
                    if not src_bytes:
                        buf = io.BytesIO(); st.session_state.active_ai_source.save(buf, format="PNG"); src_bytes = buf.getvalue()
                    
                    client = xai_sdk.Client(api_key=api_key)
                    uri = f"data:image/jpeg;base64,{base64.b64encode(src_bytes).decode('utf-8')}"
                    res = client.image.sample(model="grok-imagine-image-pro", prompt=edit_p, image_url=uri)
                    st.session_state.active_ai_source = Image.open(io.BytesIO(requests.get(res.url).content))
                    st.session_state.draft += f"[motion: transformation to {edit_p}] "

    else: # TRYB DUO
        st.subheader("👥 Duo Direct")
        up_a = st.file_uploader("Zdjęcie 1 (Postać A / TŁO):", type=['jpg','png','jpeg'])
        up_b = st.file_uploader("Zdjęcie 2 (Postać B):", type=['jpg','png','jpeg'])
        if up_a:
            if st.button("➕ Wstaw Postać A", use_container_width=True):
                st.session_state.draft += "[character: Person A from Image 1] "
        if up_b:
            if st.button("➕ Wstaw Postać B", use_container_width=True):
                st.session_state.draft += "[character: Person B from Image 2] "

    st.divider()
    if st.button("⏪ UNDO (Cofnij)", use_container_width=True):
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1]); st.rerun()
    if st.button("🗑️ CZYŚĆ WSZYSTKO", type="secondary", use_container_width=True):
        st.session_state.draft = ""; st.session_state.active_ai_source = None; st.rerun()

# --- PANEL REŻYSERSKI 3x2 ---
st.subheader("🖼️ Podgląd Materiału")
col_img, col_ui = st.columns([1, 2])
with col_img:
    if mode == "Solo (1 Osoba / AI)":
        disp = st.session_state.active_ai_source if st.session_state.active_ai_source else (Image.open(up_file) if "up_file" in locals() and up_file else None)
        if disp: st.image(disp, use_container_width=True)
    else:
        c1, c2 = st.columns(2)
        with c1: 
            if up_a: st.image(Image.open(up_a), caption="A (Główne tło)", use_container_width=True)
        with c2: 
            if up_b: st.image(Image.open(up_b), caption="B (Gość)", use_container_width=True)

with col_ui:
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.subheader("🎥 Kamera")
        sel_cam = st.selectbox("Ujęcie:", ["steady close-up", "tilt down", "full shot", "dolly zoom", "orbit shot", "handheld shake", "whip pan"])
        if st.button("➕ Kamera"): st.session_state.draft += f"[camera: {sel_cam}] "
    with r1c2:
        st.subheader("🎙️ Dialog")
        txt = st.text_input("Tekst mowy:")
        spk = st.selectbox("Mówi:", ["Osoba A", "Osoba B"]) if mode == "Duo (2 Osoby - Direct)" else None
        if st.button("➕ Dialog"):
            tag = f"person {spk[-1]}" if spk else ""
            st.session_state.draft += f"[voice: polish {tag}] \"{txt}\" [pause: 0.5s] "
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
        s_opt = st.selectbox("Efekt:", ["Applause", "Heartbeat", "Thunder", "Scream", "Door burst"])
        if st.button("➕ SFX"): st.session_state.draft += f"[audio: {s_opt.lower()}] "
    with r2c3:
        st.subheader("🎭 Głos")
        v_opt = st.selectbox("Filtr:", ["Whisper", "Radio", "Echo", "Deep Bass", "Robot"])
        if st.button("➕ Filtr"): st.session_state.draft += f"[audio: {v_opt.lower()}] "

# --- RENDER (v7.2 Stable) ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=150)

col_q, col_d = st.columns(2)
with col_q:
    res_opt = st.selectbox("Jakość (💰):", ["480p", "720p"], index=0)
with col_d:
    dur = st.slider("Długość (s):", 5, 15, 10)

if st.button("🚀 WYPAL FINALNE WIDEO", type="primary", use_container_width=True):
    if not st.session_state.draft:
        st.error("⚠️ Draft jest pusty!"); st.stop()
        
    with st.spinner(f"Renderowanie {res_opt}..."):
        try:
            c_async = xai_sdk.AsyncClient(api_key=api_key)
            
            if mode == "Solo (1 Osoba / AI)":
                if st.session_state.active_ai_source:
                    buf = io.BytesIO(); st.session_state.active_ai_source.save(buf, format="JPEG"); img_data = buf.getvalue()
                elif up_file:
                    img_data = up_file.getvalue()
                else:
                    st.error("Brak zdjęcia!"); st.stop()
                
                b64 = base64.b64encode(img_data).decode()
                coro = c_async.video.generate(
                    model="grok-imagine-video",
                    image_url=f"data:image/jpeg;base64,{b64}",
                    prompt=st.session_state.draft,
                    duration=dur,
                    resolution=res_opt
                )
            else: # DUO
                if not (up_a and up_b):
                    st.error("Wgraj oba zdjęcia!"); st.stop()
                
                b64_a = base64.b64encode(up_a.getvalue()).decode()
                b64_b = base64.b64encode(up_b.getvalue()).decode()
                coro = c_async.video.generate(
                    model="grok-imagine-video",
                    image_url=[f"data:image/jpeg;base64,{b64_a}", f"data:image/jpeg;base64,{b64_b}"],
                    prompt=st.session_state.draft,
                    duration=dur,
                    resolution=res_opt
                )
            
            # Uruchomienie asynchroniczne z nową pętlą
            res_video = run_async(coro)
            st.video(requests.get(res_video.url).content)
            st.success("🎬 Gotowe!")
            
        except Exception as e:
            st.error(f"🔴 Błąd: {str(e)}")
