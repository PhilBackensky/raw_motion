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
st.set_page_config(page_title="RAWMOTION Director's Pro", layout="wide", page_icon="🎬")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔐 Director's Entrance")
        try: correct_password = st.secrets["MY_APP_PASSWORD"]
        except: st.error("Ustaw MY_APP_PASSWORD w Secrets!"); st.stop()
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
    """Tłumaczy polski opis na techniczne tagi Memphis."""
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    prompt = f"Translate this Polish {context_type} description into ONE technical tag for Memphis engine. Use [motion: ...] or [camera: ...]. Output ONLY the tag. Text: {text}"
    payload = {
        "model": "grok-4-1-fast-non-reasoning",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        return res.json()['choices'][0]['message']['content']
    except: return f"[{context_type}: error]"

def estimate_duration(prompt):
    pauses = re.findall(r"\[pause:\s*(\d+\.?\d*)s\]", prompt)
    pause_time = sum(float(p) for p in pauses)
    clean_text = re.sub(r"\[.*?\]", "", prompt)
    words = len(clean_text.split())
    return round(pause_time + (words * 0.75) + 2.5, 1)

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director's Pro v2.5")

if "draft" not in st.session_state: st.session_state.draft = ""

# --- SIDEBAR: GLOBALNA POSTAĆ ---
with st.sidebar:
    st.header("👤 Definicja Postaci")
    char_input = st.text_area("Opisz postać po polsku:", "Fotorealistyczna kobieta ze zdjęcia, styl kinowy")
    if st.button("➕ Przetłumacz i Wstaw Postać"):
        with st.spinner("Tłumaczenie postaci..."):
            tech_char = elon_translator(char_input, "character")
            st.session_state.draft += f"{tech_char} "
    st.divider()
    if st.button("🗑️ WYCZYŚĆ SCENARIUSZ", type="secondary"):
        st.session_state.draft = ""; st.rerun()

# --- GŁÓWNY PANEL ---
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🎥 Kamera")
    cam_options = [
        "steady close-up on face", 
        "dynamic tilt down to hips", 
        "handheld shake", 
        "dolly zoom in", 
        "extreme close-up on eyes/lips",
        "low angle shot (heroic)",
        "orbit shot (rotating around)",
        "bird's eye view",
        "pan left to right"
    ]
    cam_type = st.selectbox("Wybierz ujęcie:", cam_options)
    if st.button("➕ Dodaj Kamerę"):
        st.session_state.draft += f"[camera: {cam_type}] "
        if "face" in cam_type or "close-up" in cam_type:
            st.session_state.draft += "[motion: high-fidelity facial animation, perfect lip-sync] "

with col2:
    st.subheader("🎙️ Dialog")
    dialog_text = st.text_input("Co postać mówi:")
    if st.button("➕ Dodaj Dialog"):
        if dialog_text:
            st.session_state.draft += f"[voice: polish] [pause: 0.6s] \"{dialog_text}\" [pause: 0.5s] "

with col3:
    st.subheader("💃 Akcja (AI)")
    action_text = st.text_input("Ruch (np. poprawia włosy):")
    if st.button("➕ Dodaj Akcję"):
        if action_text:
            with st.spinner("Tłumaczenie akcji..."):
                tech_tag = elon_translator(action_text, "motion")
                st.session_state.draft += f"{tech_tag} "

# --- CZAS I DRAFT ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=150)
est_time = estimate_duration(st.session_state.draft)
st.info(f"⏱️ Estymowany czas: **{est_time}s** | 💰 Koszt: **${round(est_time*0.05, 2)}**")

# --- RENDER ---
st.divider()
r_col1, r_col2 = st.columns(2)
with r_col1:
    uploaded_file = st.file_uploader("🖼️ Zdjęcie:", type=['jpg','png','jpeg'])
    final_dur = st.slider("Długość filmu (s):", 5, 15, int(min(max(est_time, 5), 15)))
with r_col2:
    if st.button("🚀 WYPAL WIDEO", type="primary", use_container_width=True):
        if uploaded_file and st.session_state.draft:
            with st.spinner("Renderowanie 'Petardy'..."):
                img_bytes = uploaded_file.getvalue()
                b64 = base64.b64encode(img_bytes).decode()
                img = Image.open(io.BytesIO(img_bytes))
                w, h = img.size
                ratio = "16:9" if w/h > 1.2 else "9:16" if w/h < 0.8 else "1:1"
                
                async def _gen():
                    client = xai_sdk.AsyncClient(api_key=api_key)
                    return await client.video.generate(model="grok-imagine-video", image_url=f"data:image/jpeg;base64,{b64}", 
                                                       prompt=st.session_state.draft, duration=final_dur, aspect_ratio=ratio)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                video = loop.run_until_complete(_gen())
                
                v_res = requests.get(video.url).content
                st.video(v_res)
                st.download_button("💾 POBIERZ MP4", v_res, "render.mp4", "video/mp4")
