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
st.set_page_config(page_title="RAWMOTION Director's Pro v5.6", layout="wide", page_icon="🎬")

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
    tag_format = "[character: ...]" if context_type == "character" else "[motion: ...]"
    prompt = f"Translate this Polish {context_type} description into ONE technical tag for Memphis engine using {tag_format}. Output ONLY the tag. Text: {text}"
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
    pauses = re.findall(r"\[pause:\s*(\d+\.?\d*)s\]", prompt)
    pause_time = sum(float(p) for p in pauses)
    audio_tags = re.findall(r"\[audio:\s*(.*?)\]", prompt)
    audio_time = len(audio_tags) * 1.5
    clean_text = re.sub(r"\[.*?\]", "", prompt)
    words = len(clean_text.split())
    return round(pause_time + (words * 0.75) + audio_time + 3.0, 1)

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director's Pro v5.6")

if "draft" not in st.session_state: st.session_state.draft = ""
if "active_image" not in st.session_state: st.session_state.active_image = None

st.divider()
uploaded_file = st.file_uploader("🖼️ KROK 1: Wgraj zdjęcie źródłowe:", type=['jpg','png','jpeg'])

# --- SIDEBAR: FX & SCENARIUSZ ---
with st.sidebar:
    st.header("👤 Zarządzanie Postacią")
    if uploaded_file:
        char_desc_pl = st.text_input("Opisz postać ze zdjęcia (PL):", "Fotorealistyczna kobieta")
        if st.button("➕ Wstaw [character] do Osi", use_container_width=True):
            with st.spinner("Tłumaczenie..."):
                st.session_state.draft += f"{elon_translator(char_desc_pl, 'character')} "

    st.divider()
    st.subheader("🛠️ Tuning FX (Edycja)")
    if uploaded_file or st.session_state.active_image:
        edit_prompt = st.text_input("Zmień coś (np. red dress):")
        if st.button("🪄 Tunuj i Wstaw FX", use_container_width=True):
            with st.spinner("Przetwarzanie..."):
                try:
                    source = uploaded_file.getvalue() if uploaded_file else None
                    if not source and st.session_state.active_image:
                        buf = io.BytesIO(); st.session_state.active_image.save(buf, format="PNG"); source = buf.getvalue()
                    res = edit_image_xai(api_key, source, edit_prompt)
                    st.session_state.active_image = Image.open(io.BytesIO(requests.get(res.url).content))
                    st.session_state.draft += f"[motion: high-fidelity realistic clothing transformation to {edit_prompt}] "
                    st.success("Tuning dodany do osi!")
                except Exception as e: st.error(f"Błąd: {e}")

    st.divider()
    if st.session_state.active_image:
        st.image(st.session_state.active_image, caption="🆕 Aktywne źródło AI Pro", use_container_width=True)
        if st.button("🗑️ Resetuj źródło"): st.session_state.active_image = None; st.rerun()
    elif uploaded_file:
        st.image(Image.open(uploaded_file), caption="Oryginał", use_container_width=True)
    
    st.divider()
    if st.button("⏪ UNDO (Cofnij krok)", use_container_width=True):
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1]); st.rerun()
    if st.button("🗑️ CZYŚĆ SCENARIUSZ", type="secondary", use_container_width=True):
        st.session_state.draft = ""; st.rerun()

# --- PANEL REŻYSERSKI 3x2 (PRZYWRÓCONA PEŁNA LISTA) ---
r1c1, r1c2, r1c3 = st.columns(3)
with r1c1:
    st.subheader("🎥 Kamera")
    cam_list = [
        "steady close-up on face — Twarz (Portret)",
        "dynamic tilt down to hips — Zjazd na biodra",
        "extreme close-up on lips — Makro (Usta)",
        "medium shot (waist up) — Plan średni",
        "full shot — Cała sylwetka",
        "over-the-shoulder — Zza ramienia",
        "dolly zoom in — Efekt Vertigo",
        "handheld shake — Z ręki (Realizm)",
        "orbit shot — Kamera krąży",
        "dutch angle — Krzywy kadr",
        "whip pan — Szybki obrót"
    ]
    sel_cam = st.selectbox("Wybierz ujęcie:", cam_list)
    if st.button("➕ Dodaj Kamerę"):
        c_p = sel_cam.split(" — ")[0]
        st.session_state.draft += f"[camera: {c_p}] "
        if any(x in c_p for x in ["face", "close-up"]):
            st.session_state.draft += "[motion: high-fidelity facial animation, perfect lip-sync] "

with r1c2:
    st.subheader("🎙️ Dialog")
    txt = st.text_input("Tekst mowy:", placeholder="Wojtek, zobacz...")
    if st.button("➕ Dodaj Dialog"):
        if txt: st.session_state.draft += f"[voice: polish] [pause: 0.6s] \"{txt}\" [pause: 0.5s] "

with r1c3:
    st.subheader("💃 Akcja")
    act = st.text_input("Ruch (PL):", placeholder="uśmiecha się zalotnie")
    if st.button("➕ Dodaj Akcję"):
        if act: st.session_state.draft += f"{elon_translator(act, 'motion')} "

r2c1, r2c2, r2c3 = st.columns(3)
with r2c1:
    st.subheader("🎵 Muzyka")
    m_list = [
        "Subtle Hip-Hop Beat — Cichy bit",
        "Cinematic Tension — Napięcie",
        "Censored Beep — Cenzura PIIIP",
        "Lo-Fi Chill — Spokojny klimat",
        "Night Club Ambient — Klub nocny",
        "Dark Techno Pulse — Mocne techno",
        "Romantic Piano — Pianino",
        "Cyberpunk Synth — Neonowy klimat"
    ]
    sel_m = st.selectbox("Podkład muzyczny:", m_list)
    if st.button("➕ Dodaj Audio"):
        st.session_state.draft += f"[audio: background {sel_m.split(' — ')[0].lower()}] "

with r2c2:
    st.subheader("🔊 SFX")
    sfx_list = [
        "Crowd Applause — Oklaski",
        "Heavy Breathing — Ciężki oddech",
        "Heartbeat Thump — Bicie serca",
        "Camera Shutter — Migawka",
        "Thunder Clap — Grzmot",
        "Glass Shatter — Rozbite szkło",
        "Deep Woosh — Świst",
        "Car Engine Rev — Silnik"
    ]
    sel_sfx = st.selectbox("Efekt SFX:", sfx_list)
    if st.button("➕ Dodaj SFX"):
        st.session_state.draft += f"[audio: {sel_sfx.split(' — ')[0].lower()}] "

with r2c3:
    st.subheader("🎭 Głos")
    voice_list = [
        "Whisper — Szept",
        "Robot Voice — Robot",
        "Radio Filter — Przez telefon",
        "Deep Bass Voice — Niski bas",
        "Echo Reverb — Echo w hali",
        "Drunk Slur — Bełkot"
    ]
    sel_v = st.selectbox("Styl głosu:", voice_list)
    if st.button("➕ Dodaj Filtr"):
        st.session_state.draft += f"[audio: {sel_v.split(' — ')[0].lower()}] "

# --- RENDER HD ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=120)
est = estimate_duration(st.session_state.draft)

col_a, col_b = st.columns(2)
with col_a:
    res_opt = st.selectbox("Jakość:", ["720p", "480p"], index=0)
with col_b:
    dur = st.slider("Długość (s):", 5, 15, int(min(max(est, 5), 15)))

if st.button("🚀 WYPAL FINALNE WIDEO (HD)", type="primary", use_container_width=True):
    img = st.session_state.active_image if st.session_state.active_image else (Image.open(uploaded_file) if uploaded_file else None)
    if img:
        with st.spinner(f"Renderowanie w {res_opt}..."):
            buf = io.BytesIO(); img.save(buf, format="JPEG"); b64 = base64.b64encode(buf.getvalue()).decode()
            async def _gen():
                c = xai_sdk.AsyncClient(api_key=api_key)
                return await c.video.generate(
                    model="grok-imagine-video", 
                    image_url=f"data:image/jpeg;base64,{b64}", 
                    prompt=st.session_state.draft, 
                    duration=dur,
                    resolution=res_opt,
                    timeout=timedelta(minutes=10)
                )
            try:
                loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); video = loop.run_until_complete(_gen())
                if video.respect_moderation:
                    v_res = requests.get(video.url).content
                    st.video(v_res); st.download_button("💾 POBIERZ", v_res, "final.mp4", "video/mp4")
                else: st.error("⚠️ Zablokowane przez moderację.")
            except Exception as e: st.error(f"Błąd: {e}")
    else: st.error("⚠️ Brak zdjęcia źródłowego!")
