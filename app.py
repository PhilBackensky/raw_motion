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
st.set_page_config(page_title="RAWMOTION Director's Pro v4.1", layout="wide", page_icon="🎬")

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
    tag_format = "[motion: ...]" if context_type in ["character", "motion"] else "[camera: ...]"
    prompt = f"Translate this Polish {context_type} description into ONE technical tag for Memphis engine using {tag_format}. Output ONLY the tag. Text: {text}"
    payload = {"model": "grok-4-1-fast-non-reasoning", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    try:
        res = requests.post(url, headers=headers, json=payload)
        return res.json()['choices'][0]['message']['content']
    except: return f"[{context_type}: error]"

# --- POPRAWIONA FUNKCJA EDYCJI (Base64 JSON) ---
def edit_image_xai(api_key, img_bytes, prompt):
    """Edytuje obraz - Wersja Multipart (najbardziej stabilna)."""
    url = "https://api.x.ai/v1/images/edits"
    
    # WAŻNE: W multipart NIE ustawiamy Content-Type ręcznie, 
    # biblioteka requests sama wygeneruje odpowiedni 'boundary'.
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    # Plik przesyłamy w słowniku 'files'
    files = {
        "image": ("image.jpg", img_bytes, "image/jpeg")
    }
    
    # Pozostałe dane (model, prompt) przesyłamy w 'data'
    data = {
        "model": "grok-imagine-image-pro",
        "prompt": prompt
    }
    
    res = requests.post(url, headers=headers, files=files, data=data)
    
    if res.status_code == 200:
        return res.json()['data'][0]['url']
    else:
        # Debug błędu, żebyśmy widzieli co dokładnie mu nie pasuje
        raise Exception(f"Błąd API {res.status_code}: {res.text}")
def estimate_duration(prompt):
    pauses = re.findall(r"\[pause:\s*(\d+\.?\d*)s\]", prompt)
    pause_time = sum(float(p) for p in pauses)
    audio_tags = re.findall(r"\[audio:\s*(.*?)\]", prompt)
    audio_time = len(audio_tags) * 1.5
    clean_text = re.sub(r"\[.*?\]", "", prompt)
    words = len(clean_text.split())
    return round(pause_time + (words * 0.75) + audio_time + 3.0, 1)

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director's Pro v4.1")

if "draft" not in st.session_state: st.session_state.draft = ""
if "ztunowane_zdjecie" not in st.session_state: st.session_state.ztunowane_zdjecie = None

st.divider()
uploaded_file = st.file_uploader("🖼️ KROK 1: Wgraj zdjęcie źródłowe:", type=['jpg','png','jpeg'])

# --- SIDEBAR: FX STUDIO ---
with st.sidebar:
    st.header("👤 Postać")
    char_desc_pl = st.text_area("Opis polski:", "Fotorealistyczna kobieta")
    if st.button("➕ Wstaw Postać", use_container_width=True):
        with st.spinner("Tłumaczenie..."):
            st.session_state.draft += f"{elon_translator(char_desc_pl, 'character')} "
    
    st.divider()
    st.subheader("🆕 Tuning Zdjęcia (FX)")
    tuning_mode = st.selectbox("Tryb:", ["Brak", "Stylizacja (Img2Img)", "Inpainting"])
    
    if tuning_mode != "Brak" and uploaded_file:
        tuning_prompt = st.text_input("Zmiana (PL):", placeholder="zmień strój na zieloną sukienkę")
        if st.button("🛠️ Tunuj Zdjęcie", use_container_width=True):
            with st.spinner("Pracuję nad obrazem..."):
                try:
                    # 1. Tłumaczenie na techniczny angielski
                    translated = elon_translator(tuning_prompt, "action")
                    clean_p = re.sub(r"\[.*?\]", "", translated).strip()
                    # 2. Wywołanie poprawionego API
                    img_url = edit_image_xai(api_key, uploaded_file.getvalue(), clean_p)
                    # 3. Zapisanie efektu
                    st.session_state.ztunowane_zdjecie = Image.open(io.BytesIO(requests.get(img_url).content))
                    st.success("Gotowe!")
                except Exception as e:
                    st.error(f"⚠️ {e}")
    
    st.divider()
    if st.session_state.ztunowane_zdjecie:
        st.image(st.session_state.ztunowane_zdjecie, caption="Aktywne źródło AI", use_container_width=True)
        if st.button("🗑️ Usuń tuning", use_container_width=True):
            st.session_state.ztunowane_zdjecie = None; st.rerun()
    elif uploaded_file:
        st.image(Image.open(uploaded_file), caption="Oryginał", use_container_width=True)
    
    st.divider()
    if st.button("⏪ UNDO", use_container_width=True):
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1]); st.rerun()
    if st.button("🗑️ CZYŚĆ DRAFT", use_container_width=True):
        st.session_state.draft = ""; st.rerun()

# --- PANEL REŻYSERSKI 3x2 ---
r1c1, r1c2, r1c3 = st.columns(3)
with r1c1:
    st.subheader("🎥 Kamera")
    cam_list = ["steady close-up on face — Twarz", "dynamic tilt down to hips — Biodra", "extreme close-up on lips — Usta", "medium shot (waist up) — Średni", "full shot — Cała", "dolly zoom in — Vertigo", "handheld shake — Drżenie"]
    sel_cam = st.selectbox("Ujęcie:", cam_list)
    if st.button("➕ Dodaj Kamerę"):
        c_p = sel_cam.split(" — ")[0]
        st.session_state.draft += f"[camera: {c_p}] "
        if "face" in c_p or "close-up" in c_p: st.session_state.draft += "[motion: high-fidelity facial animation, perfect lip-sync] "

with r1c2:
    st.subheader("🎙️ Dialog")
    txt = st.text_input("Mowa:")
    if st.button("➕ Dodaj Mowę"):
        if txt: st.session_state.draft += f"[voice: polish] [pause: 0.6s] \"{txt}\" [pause: 0.5s] "

with r1c3:
    st.subheader("💃 Akcja")
    act = st.text_input("Ruch (PL):")
    if st.button("➕ Dodaj Ruch"):
        if act: st.session_state.draft += f"{elon_translator(act, 'motion')} "

st.divider()
r2c1, r2c2, r2c3 = st.columns(3)
with r2c1:
    st.subheader("🎵 Muzyka")
    m_opt = st.selectbox("Muzyka:", ["Subtle Hip-Hop Beat", "Cinematic Tension", "Censored Beep", "Lo-Fi Chill"])
    if st.button("➕ Audio"): st.session_state.draft += f"[audio: background {m_opt.lower()}] "
with r2c2:
    st.subheader("🔊 SFX")
    s_opt = st.selectbox("SFX:", ["Crowd Applause", "Heavy Breathing", "Heartbeat Thump", "Thunder Clap"])
    if st.button("➕ SFX"): st.session_state.draft += f"[audio: {s_opt.lower()}] "
with r2c3:
    st.subheader("🎭 Filtry")
    v_opt = st.selectbox("Styl:", ["Whisper", "Radio Filter", "Echo Reverb"])
    if st.button("➕ Filtr"): st.session_state.draft += f"[audio: {v_opt.lower()}] "

# --- RENDER ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU:", value=st.session_state.draft, height=120)
est = estimate_duration(st.session_state.draft)
st.info(f"⏱️ Czas: {est}s | 💰 Koszt: ${round(est*0.05, 2)}")

dur = st.slider("Długość (s):", 5, 15, int(min(max(est, 5), 15)))
if st.button("🚀 WYPAL WIDEO", type="primary", use_container_width=True):
    img = st.session_state.ztunowane_zdjecie if st.session_state.ztunowane_zdjecie else (Image.open(uploaded_file) if uploaded_file else None)
    if img:
        with st.spinner("Renderuję 'Petardę'..."):
            buf = io.BytesIO(); img.save(buf, format="JPEG"); b64 = base64.b64encode(buf.getvalue()).decode()
            async def _gen():
                c = xai_sdk.AsyncClient(api_key=api_key)
                return await c.video.generate(model="grok-imagine-video", image_url=f"data:image/jpeg;base64,{b64}", prompt=st.session_state.draft, duration=dur, aspect_ratio="1:1" if img.size[0]/img.size[1] < 1.1 else "16:9")
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); video = loop.run_until_complete(_gen())
            v_res = requests.get(video.url).content
            st.video(v_res); st.download_button("💾 POBIERZ", v_res, "render.mp4", "video/mp4")
