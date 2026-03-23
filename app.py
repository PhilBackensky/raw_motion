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
st.set_page_config(page_title="RAWMOTION Director's Pro v3.5", layout="wide", page_icon="🎬")

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
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # Precyzyjne wymuszanie tagów
    tag_format = "[motion: ...]" if context_type in ["character", "motion"] else "[camera: ...]"
    
    prompt = f"Translate this Polish {context_type} description into ONE technical tag for Memphis engine using {tag_format}. Output ONLY the tag. Text: {text}"
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
    audio_tags = re.findall(r"\[audio:\s*(.*?)\]", prompt)
    audio_time = len(audio_tags) * 1.5
    clean_text = re.sub(r"\[.*?\]", "", prompt)
    words = len(clean_text.split())
    return round(pause_time + (words * 0.75) + audio_time + 3.0, 1)

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director's Pro v3.5")

if "draft" not in st.session_state: st.session_state.draft = ""

# Sidebar: Postać i Undo
with st.sidebar:
    st.header("👤 Definicja Postaci")
    char_input = st.text_area("Opisz postać po polsku:", "Fotorealistyczna kobieta ze zdjęcia, styl kinowy")
    if st.button("➕ Tłumacz i Wstaw Postać", use_container_width=True):
        with st.spinner("Tłumaczenie..."):
            st.session_state.draft += f"{elon_translator(char_input, 'character')} "
    
    st.divider()
    if st.button("⏪ COFNIJ (UNDO)", use_container_width=True):
        # Usuwa ostatni element w nawiasach kwadratowych lub ostatnie słowo
        pattern = r"\[.*?\]\s*$"
        if re.search(pattern, st.session_state.draft.strip()):
            st.session_state.draft = re.sub(pattern, "", st.session_state.draft.strip())
        else:
            words = st.session_state.draft.strip().split()
            if words: st.session_state.draft = " ".join(words[:-1])
        st.rerun()

    if st.button("🗑️ WYCZYŚĆ WSZYSTKO", type="secondary", use_container_width=True):
        st.session_state.draft = ""; st.rerun()

# --- PANEL REŻYSERSKI (2 RZĘDY X 3 KOLUMNY) ---
row1_col1, row1_col2, row1_col3 = st.columns(3)

with row1_col1:
    st.subheader("🎥 Kamera")
    cam_type = st.selectbox("Ujęcie:", [
        "steady close-up on face", "dynamic tilt down to hips", "extreme close-up on lips",
        "medium shot (waist up)", "full shot", "over-the-shoulder", "dolly zoom in", 
        "handheld shake", "orbit shot", "dutch angle", "whip pan"
    ])
    if st.button("➕ Dodaj Kamerę"):
        st.session_state.draft += f"[camera: {cam_type}] "
        if any(x in cam_type for x in ["face", "close-up"]):
            st.session_state.draft += "[motion: high-fidelity facial animation, perfect lip-sync] "

with row1_col2:
    st.subheader("🎙️ Dialog")
    dialog_text = st.text_input("Tekst mowy:", placeholder="Wojtek, chcesz?")
    if st.button("➕ Dodaj Dialog"):
        if dialog_text:
            st.session_state.draft += f"[voice: polish] [pause: 0.6s] \"{dialog_text}\" [pause: 0.5s] "

with row1_col3:
    st.subheader("💃 Akcja (AI)")
    action_input = st.text_input("Ruch:", placeholder="mruga okiem i uśmiecha się")
    if st.button("➕ Dodaj Akcję"):
        if action_input:
            with st.spinner("Tłumaczenie..."):
                st.session_state.draft += f"{elon_translator(action_input, 'motion')} "

st.divider()
row2_col1, row2_col2, row2_col3 = st.columns(3)

with row2_col1:
    st.subheader("🎵 Muzyka & Tło")
    music_opt = st.selectbox("Muzyka:", [
        "Subtle Hip-Hop Beat", "Cinematic Tension", "Censored Beep", "Lo-Fi Chill", 
        "Night Club Ambient", "Dark Techno Pulse", "Romantic Piano"
    ])
    if st.button("➕ Dodaj Audio"):
        st.session_state.draft += f"[audio: background {music_opt.lower()}] "

with row2_col2:
    st.subheader("🔊 Efekty SFX")
    sfx_opt = st.selectbox("SFX:", [
        "Crowd Applause", "Heavy Breathing", "Heartbeat Thump", "Camera Shutter", 
        "Thunder Clap", "Glass Shatter", "Deep Woosh"
    ])
    if st.button("➕ Dodaj SFX"):
        st.session_state.draft += f"[audio: {sfx_opt.lower()}] "

with row2_col3:
    st.subheader("🎭 Głos & Specjalne")
    voice_opt = st.selectbox("Filtr:", ["Whisper", "Robot Voice", "Radio Filter", "Deep Bass Voice", "Echo Reverb"])
    if st.button("➕ Dodaj Filtr"):
        st.session_state.draft += f"[audio: {voice_opt.lower()}] "

# --- CZAS I DRAFT ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=120)
est_time = estimate_duration(st.session_state.draft)
st.info(f"⏱️ Estymowany czas: **{est_time}s** | 💰 Koszt: **${round(est_time*0.05, 2)}**")

# --- RENDER ---
r_col1, r_col2 = st.columns(2)
with r_col1:
    uploaded_file = st.file_uploader("🖼️ Zdjęcie:", type=['jpg','png','jpeg'])
with r_col2:
    final_dur = st.slider("Długość filmu (s):", 5, 15, int(min(max(est_time, 5), 15)))
    if st.button("🚀 WYPAL WIDEO", type="primary", use_container_width=True):
        if uploaded_file and st.session_state.draft:
            with st.spinner("Renderowanie..."):
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
                st.download_button("💾 POBIERZ", v_res, "render.mp4", "video/mp4")
