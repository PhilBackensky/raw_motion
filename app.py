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
st.set_page_config(page_title="RAWMOTION Direct Duo v6.5", layout="wide", page_icon="🎬")

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

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Direct Duo v6.5")

if "draft" not in st.session_state: st.session_state.draft = ""

# --- SIDEBAR: DWA SLOTY BEZ FUZJI ---
with st.sidebar:
    st.header("👥 Obsada Duo")
    up_a = st.file_uploader("Osoba A (np. ta w bieli):", type=['jpg','png','jpeg'])
    up_b = st.file_uploader("Osoba B (np. ta w różu):", type=['jpg','png','jpeg'])
    
    st.divider()
    if up_a:
        if st.button("➕ Wstaw Postać A do Osi", use_container_width=True):
            st.session_state.draft += "[character: Person A from Image 1] "
    if up_b:
        if st.button("➕ Wstaw Postać B do Osi", use_container_width=True):
            st.session_state.draft += "[character: Person B from Image 2] "
            
    st.divider()
    if st.button("⏪ UNDO", use_container_width=True):
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1]); st.rerun()
    if st.button("🗑️ CZYŚĆ SCENARIUSZ", type="secondary", use_container_width=True):
        st.session_state.draft = ""; st.rerun()

# --- PANEL REŻYSERSKI ---
col_img, col_ui = st.columns([1, 2])
with col_img:
    if up_a or up_b:
        ca, cb = st.columns(2)
        with ca: 
            if up_a: st.image(Image.open(up_a), caption="Image 1", use_container_width=True)
        with cb: 
            if up_b: st.image(Image.open(up_b), caption="Image 2", use_container_width=True)
    else: st.info("Wgraj oba zdjęcia.")

with col_ui:
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.subheader("🎥 Kamera")
        sel_cam = st.selectbox("Ujęcie:", ["medium shot", "close-up", "orbit shot", "handheld shake"])
        if st.button("➕ Kamera"): st.session_state.draft += f"[camera: {sel_cam}] "
    with r1c2:
        st.subheader("🎙️ Dialog")
        txt = st.text_input("Tekst mowy:")
        if st.button("➕ Dialog"): st.session_state.draft += f"[voice: polish] \"{txt}\" [pause: 0.5s] "
    with r1c3:
        st.subheader("💃 Ruch")
        act = st.text_input("Akcja (PL):")
        if st.button("➕ Ruch"): st.session_state.draft += f"{elon_translator(act, 'motion')} "

# --- RENDER DIRECT DUO ---
st.divider()
st.session_state.draft = st.text_area("🛠️ DRAFT (WPISZ TUTAJ SCENARIUSZ KONFRONTACJI):", value=st.session_state.draft, height=150)
dur = st.slider("Długość (s):", 5, 15, 10)

if st.button("🚀 WYPAL DUO-WIDEO (BEZPOŚREDNIO)", type="primary", use_container_width=True):
    if up_a and up_b and st.session_state.draft:
        with st.spinner("Wysyłam oba zdjęcia do Memphis..."):
            # Kodujemy oba zdjęcia
            b64_a = base64.b64encode(up_a.getvalue()).decode()
            b64_b = base64.b64encode(up_b.getvalue()).decode()
            
            async def _gen_direct_duo():
                c = xai_sdk.AsyncClient(api_key=api_key)
                # Przesyłamy listę obrazów bezpośrednio do generatora wideo
                # Memphis obsługuje image_url jako listę lub wielokrotne referencje w prompcie
                return await c.video.generate(
                    model="grok-imagine-video", 
                    # Zgodnie z dokumentacją: podajemy listę URLi lub Base64
                    image_url=[f"data:image/jpeg;base64,{b64_a}", f"data:image/jpeg;base64,{b64_b}"],
                    prompt=st.session_state.draft, 
                    duration=dur, 
                    resolution="720p",
                    timeout=timedelta(minutes=15)
                )
            try:
                loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); video = loop.run_until_complete(_gen_direct_duo())
                st.video(requests.get(video.url).content)
            except Exception as e: st.error(f"Błąd: {e}")
