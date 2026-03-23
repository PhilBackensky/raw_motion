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
st.set_page_config(page_title="RAWMOTION Director's Pro v5", layout="wide", page_icon="🎬")

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

# --- NOWA FUNKCJA API: STABILNE GENEROWANIE OBRAZU ---
def generate_image_xai(api_key, prompt, model_name="grok-imagine-image-pro"):
    """Generuje nowy obraz przy użyciu Grok Imagine Pro."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def _async_gen():
        client = xai_sdk.AsyncClient(api_key=api_key)
        # Używamy wybranego modelu (standard lub pro)
        return await client.image.generate(
            model=model_name,
            prompt=prompt,
            aspect_ratio="1:1", # Najlepsze do twarzy wideo
            safe_mode="standard"
        )
    try: return loop.run_until_complete(_async_gen())
    finally: loop.close()

def estimate_duration(prompt):
    pauses = re.findall(r"\[pause:\s*(\d+\.?\d*)s\]", prompt)
    pause_time = sum(float(p) for p in pauses)
    audio_tags = re.findall(r"\[audio:\s*(.*?)\]", prompt)
    audio_time = len(audio_tags) * 1.5
    clean_text = re.sub(r"\[.*?\]", "", prompt)
    words = len(clean_text.split())
    return round(pause_time + (words * 0.75) + audio_time + 3.0, 1)

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director's Pro v5.0 (Stabilne Studio FX)")

if "draft" not in st.session_state: st.session_state.draft = ""
if "ztunowane_zdjecie" not in st.session_state: st.session_state.ztunowane_zdjecie = None

st.divider()
uploaded_file = st.file_uploader("🖼️ KROK 1: Wgraj zdjęcie źródłowe (lub wygeneruj w pasku bocznym):", type=['jpg','png','jpeg'])

# --- SIDEBAR: FX STUDIO (ROZBUDOWANY O GENERATOR) ---
with st.sidebar:
    st.header("👤 Postać w Filmie")
    char_desc_pl = st.text_area("Opis fizyczny (PL):", "Fotorealistyczna kobieta")
    if st.button("➕ Wstaw do Osi", use_container_width=True):
        with st.spinner("Tłumaczenie..."):
            st.session_state.draft += f"{elon_translator(char_desc_pl, 'character')} "
    
    st.divider()
    
    # === NOWA SEKCJA: KREATOR POSTACI AI (Zamiast niedziałającego Tuningu) ===
    st.subheader("🆕 Kreator Postaci (Grok Pro)")
    image_prompt = st.text_area("Opisz nową postać (ang/pl - lepiej ang):", 
                                placeholder="A close-up photograph of Ana de Armas in a tight GREEN dress, cinematic, photorealistic, 35mm")
    
    img_model_opt = st.selectbox("Wybierz model ($):", ["Standard ($0.02)", "Pro ($0.07)"])
    img_model_pure = "grok-imagine-image" if "Standard" in img_model_opt else "grok-imagine-image-pro"
    
    if st.button("🚀 Generuj Nową Postać", use_container_width=True):
        if image_prompt:
            with st.spinner("Grok generuje postać..."):
                try:
                    # 1. Wywołanie STABILNEGO API generowania
                    ai_res = generate_image_xai(api_key, image_prompt, img_model_pure)
                    # 2. Pobranie i zapisanie obrazu
                    img_data = requests.get(ai_res.url).content
                    st.session_state.ztunowane_zdjecie = Image.open(io.BytesIO(img_data))
                    st.success("Twarz wygenerowana!")
                except Exception as e:
                    st.error(f"⚠️ Błąd: {e}")
        else:
            st.error("Wpisz opis dla zdjęcia!")

    st.divider()
    
    # === WYŚWIETLANIE PODGLĄDU (WGGRANEGO LUB AI) ===
    if st.session_state.ztunowane_zdjecie:
        st.image(st.session_state.ztunowane_zdjecie, caption="🆕 Aktywne źródło (AI Pro)", use_container_width=True)
        if st.button("🗑️ Usuń zdjęcie AI", use_container_width=True):
            st.session_state.ztunowane_zdjecie = None; st.rerun()
    elif uploaded_file:
        st.image(Image.open(uploaded_file), caption="Oryginał", use_container_width=True)
    
    st.divider()
    # Zarządzanie draftem
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
    # NOWA LOGIKA: Wybiera zdjęcie wygenerowane AI, potem wgrane
    img = st.session_state.ztunowane_zdjecie if st.session_state.ztunowane_zdjecie else (Image.open(uploaded_file) if uploaded_file else None)
    
    if img and st.session_state.draft:
        with st.spinner("Produkcja 'Petardy' trwa..."):
            buf = io.BytesIO(); img.save(buf, format="JPEG"); b64 = base64.b64encode(buf.getvalue()).decode()
            async def _gen():
                c = xai_sdk.AsyncClient(api_key=api_key)
                # Używamy najdroższego i najlepszego modelu wideo
                return await c.video.generate(
                    model="grok-imagine-video", 
                    image_url=f"data:image/jpeg;base64,{b64}", 
                    prompt=st.session_state.draft, 
                    duration=dur, 
                    aspect_ratio="1:1" if img.size[0]/img.size[1] < 1.1 else "16:9"
                )
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); video = loop.run_until_complete(_gen())
            v_res = requests.get(video.url).content
            st.video(v_res); st.download_button("💾 POBIERZ KLIP", v_res, "render_v50.mp4", "video/mp4")
    else:
        st.error("⚠️ Wgraj zdjęcie lub wygeneruj nową postać, a potem przygotuj scenariusz!")
