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
st.set_page_config(page_title="RAWMOTION Director's Pro v4.2", layout="wide", page_icon="🎬")

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

def edit_image_xai(api_key, img_bytes, prompt):
    """Edytuje obraz przy użyciu standardu Data URI (Base64)."""
    url = "https://api.x.ai/v1/images/edits"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Kodowanie obrazu do Base64 z nagłówkiem MIME
    img_b64 = base64.b64encode(img_bytes).decode('utf-8')
    data_uri = f"data:image/jpeg;base64,{img_b64}"
    
    payload = {
        "model": "grok-imagine-image-pro",
        "image": data_uri,
        "prompt": prompt
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            return res.json()['data'][0]['url']
        elif res.status_code == 502:
            raise Exception("Serwer xAI jest przeciążony (502). Spróbuj ponownie za chwilę.")
        else:
            # Próba wyciągnięcia błędu z JSONa, jeśli istnieje
            err_msg = res.text
            try: err_msg = res.json().get('error', {}).get('message', res.text)
            except: pass
            raise Exception(f"Błąd API {res.status_code}: {err_msg}")
    except requests.exceptions.Timeout:
        raise Exception("Upłynął czas oczekiwania na odpowiedź serwera.")

def estimate_duration(prompt):
    pauses = re.findall(r"\[pause:\s*(\d+\.?\d*)s\]", prompt)
    pause_time = sum(float(p) for p in pauses)
    audio_tags = re.findall(r"\[audio:\s*(.*?)\]", prompt)
    audio_time = len(audio_tags) * 1.5
    clean_text = re.sub(r"\[.*?\]", "", prompt)
    words = len(clean_text.split())
    return round(pause_time + (words * 0.75) + audio_time + 3.0, 1)

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director's Pro v4.2")

if "draft" not in st.session_state: st.session_state.draft = ""
if "ztunowane_zdjecie" not in st.session_state: st.session_state.ztunowane_zdjecie = None

st.divider()
uploaded_file = st.file_uploader("🖼️ KROK 1: Wgraj zdjęcie źródłowe:", type=['jpg','png','jpeg'])

# --- SIDEBAR: FX STUDIO ---
with st.sidebar:
    st.header("👤 Postać")
    char_desc_pl = st.text_area("Opis fizyczny (PL):", "Fotorealistyczna kobieta")
    if st.button("➕ Wstaw do Osi", use_container_width=True):
        with st.spinner("Tłumaczenie..."):
            st.session_state.draft += f"{elon_translator(char_desc_pl, 'character')} "
    
    st.divider()
    st.subheader("🆕 Tuning Zdjęcia (FX)")
    tuning_mode = st.selectbox("Wybierz tryb:", ["Brak", "Stylizacja (Img2Img)", "Inpainting (Zmiana)"])
    
    if tuning_mode != "Brak" and uploaded_file:
        tuning_prompt = st.text_input("Opisz zmianę (PL):", placeholder="zmień sukienkę na zieloną")
        if st.button("🛠️ Wykonaj FX", use_container_width=True):
            with st.spinner("Grok pracuje nad obrazem..."):
                try:
                    # Tłumaczenie promptu na techniczny angielski
                    translated = elon_translator(tuning_prompt, "action")
                    clean_p = re.sub(r"\[.*?\]", "", translated).strip()
                    # Wywołanie poprawionego API FX
                    img_url = edit_image_xai(api_key, uploaded_file.getvalue(), clean_p)
                    # Pobranie wyniku
                    res_img = requests.get(img_url).content
                    st.session_state.ztunowane_zdjecie = Image.open(io.BytesIO(res_img))
                    st.success("Tuning zakończony!")
                except Exception as e:
                    st.error(f"⚠️ {e}")
    
    st.divider()
    if st.session_state.ztunowane_zdjecie:
        st.image(st.session_state.ztunowane_zdjecie, caption="Aktywne źródło FX", use_container_width=True)
        if st.button("🗑️ Cofnij Tuning", use_container_width=True):
            st.session_state.ztunowane_zdjecie = None; st.rerun()
    elif uploaded_file:
        st.image(Image.open(uploaded_file), caption="Oryginał", use_container_width=True)
    
    st.divider()
    if st.button("⏪ UNDO (Cofnij krok)", use_container_width=True):
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1]); st.rerun()
    if st.button("🗑️ CZYŚĆ SCENARIUSZ", type="secondary", use_container_width=True):
        st.session_state.draft = ""; st.rerun()

# --- PANEL REŻYSERSKI 3x2 ---
r1c1, r1c2, r1c3 = st.columns(3)
with r1c1:
    st.subheader("🎥 Kamera")
    cam_list = [
        "steady close-up on face — Portret", 
        "dynamic tilt down to hips — Na biodra", 
        "extreme close-up on lips — Makro usta", 
        "medium shot (waist up) — Od pasa", 
        "full shot — Cała sylwetka", 
        "dolly zoom in — Efekt szoku", 
        "handheld shake — Z ręki"
    ]
    sel_cam = st.selectbox("Ujęcie:", cam_list)
    if st.button("➕ Dodaj Kamerę"):
        c_p = sel_cam.split(" — ")[0]
        st.session_state.draft += f"[camera: {c_p}] "
        if "face" in c_p or "close-up" in c_p: st.session_state.draft += "[motion: high-fidelity facial animation, perfect lip-sync] "

with r1c2:
    st.subheader("🎙️ Dialog")
    txt = st.text_input("Co mówi postać:", placeholder="Wojtek, zobacz moją sukienkę!")
    if st.button("➕ Dodaj Dialog"):
        if txt: st.session_state.draft += f"[voice: polish] [pause: 0.6s] \"{txt}\" [pause: 0.5s] "

with r1c3:
    st.subheader("💃 Ruch")
    act = st.text_input("Opisz akcję (PL):", placeholder="uśmiecha się zalotnie")
    if st.button("➕ Dodaj Ruch"):
        if act: 
            with st.spinner("Tłumaczenie ruchu..."):
                st.session_state.draft += f"{elon_translator(act, 'motion')} "

st.divider()
r2c1, r2c2, r2c3 = st.columns(3)
with r2c1:
    st.subheader("🎵 Muzyka")
    m_opt = st.selectbox("Podkład:", ["Subtle Hip-Hop Beat", "Cinematic Tension", "Censored Beep", "Lo-Fi Chill"])
    if st.button("➕ Dodaj Muzykę"): st.session_state.draft += f"[audio: background {m_opt.lower()}] "
with r2c2:
    st.subheader("🔊 SFX")
    s_opt = st.selectbox("Efekt:", ["Crowd Applause", "Heavy Breathing", "Heartbeat Thump", "Thunder Clap"])
    if st.button("➕ Dodaj SFX"): st.session_state.draft += f"[audio: {s_opt.lower()}] "
with r2c3:
    st.subheader("🎭 Filtr")
    v_opt = st.selectbox("Głos:", ["Whisper", "Radio Filter", "Echo Reverb"])
    if st.button("➕ Dodaj Filtr"): st.session_state.draft += f"[audio: {v_opt.lower()}] "

# --- DRAFT I RENDER ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=120)
est = estimate_duration(st.session_state.draft)
st.info(f"⏱️ Estymowany czas: {est}s | 💰 Koszt: ${round(est*0.05, 2)}")

dur = st.slider("Czas trwania filmu (s):", 5, 15, int(min(max(est, 5), 15)))
if st.button("🚀 WYPAL FINALNE WIDEO", type="primary", use_container_width=True):
    # Wybór obrazu: najpierw FX, potem oryginał
    img = st.session_state.ztunowane_zdjecie if st.session_state.ztunowane_zdjecie else (Image.open(uploaded_file) if uploaded_file else None)
    
    if img and st.session_state.draft:
        with st.spinner("Produkcja 'Petardy' trwa..."):
            buf = io.BytesIO(); img.save(buf, format="JPEG"); b64 = base64.b64encode(buf.getvalue()).decode()
            async def _gen():
                c = xai_sdk.AsyncClient(api_key=api_key)
                return await c.video.generate(
                    model="grok-imagine-video", 
                    image_url=f"data:image/jpeg;base64,{b64}", 
                    prompt=st.session_state.draft, 
                    duration=dur, 
                    aspect_ratio="1:1" if img.size[0]/img.size[1] < 1.1 else "16:9"
                )
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); video = loop.run_until_complete(_gen())
            v_res = requests.get(video.url).content
            st.video(v_res); st.download_button("💾 POBIERZ KLIP", v_res, "render_v42.mp4", "video/mp4")
    else:
        st.error("⚠️ Wgraj zdjęcie i przygotuj scenariusz!")
