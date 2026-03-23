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
st.set_page_config(page_title="RAWMOTION Director's Pro v5.6 Ultra", layout="wide", page_icon="🎬")

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

# FUNKCJA GENEROWANIA OBRAZU (OD ZERA)
def generate_image_xai(api_key, prompt, model_name="grok-imagine-image-pro"):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def _async_gen():
        client = xai_sdk.AsyncClient(api_key=api_key)
        # Zgodnie z dokumentacją: używamy .sample()
        return await client.image.sample(model=model_name, prompt=prompt, aspect_ratio="1:1")
    try: return loop.run_until_complete(_async_gen())
    finally: loop.close()

# FUNKCJA EDYCJI OBRAZU (FX)
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
st.title("🎥 RAWMOTION Director's Pro v5.6 (Zintegrowane Studio FX)")

if "draft" not in st.session_state: st.session_state.draft = ""
if "active_ai_image" not in st.session_state: st.session_state.active_ai_image = None

st.divider()
uploaded_file = st.file_uploader("🖼️ KROK 1: Wgraj zdjęcie źródłowe z dysku (Opcjonalnie):", type=['jpg','png','jpeg'])

# --- SIDEBAR: FX & KREATOR ---
with st.sidebar:
    st.header("👤 Zarządzanie Postacią")
    
    # Używamy Tabs, aby zmieścić generator i edytor bez bałaganu
    tab_gen, tab_edit = st.tabs(["✨ Generator", "🖼️ Twoje Zdjęcie / FX"])
    
    with tab_gen:
        st.subheader("Nowa Postać AI (Text-to-Image)")
        gen_model_opt = st.selectbox("Wybierz model ($):", ["Standard ($0.02)", "Pro ($0.07)"])
        gen_model_pure = "grok-imagine-image" if "Standard" in gen_model_opt else "grok-imagine-image-pro"
        gen_prompt = st.text_area("Opisz postać (ang/pl):", placeholder="A photograph of a beautiful woman in a green dress...")
        if st.button("🚀 Generuj Postać AI", use_container_width=True):
            if gen_prompt:
                with st.spinner("Grok tworzy postać..."):
                    try:
                        res = generate_image_xai(api_key, gen_prompt, model_name=gen_model_pure)
                        st.session_state.active_ai_image = Image.open(io.BytesIO(requests.get(res.url).content))
                        st.success("Postać wygenerowana i ustawiona jako źródło!")
                    except Exception as e: st.error(f"Błąd generowania: {e}")
            else:
                st.error("Opisz kogo wygenerować!")
        if st.session_state.active_ai_image:
            if st.button("🗑️ Usuń źródło AI", type="secondary", use_container_width=True):
                st.session_state.active_ai_image = None; st.rerun()

    with tab_edit:
        # WGRANE ZDJĘCIE
        if uploaded_file:
            st.subheader("Opisz Zdjęcie z Dysku (Wgrane)")
            uploaded_desc_pl = st.text_input("Opis polski:", "Fotorealistyczna kobieta")
            if st.button("➕ Wstaw Opis do Osi", use_container_width=True):
                with st.spinner("Tłumaczenie..."):
                    st.session_state.draft += f"{elon_translator(uploaded_desc_pl, 'character')} "
                    st.success("Opis dodany do draftu!")
            st.divider()

        # TUNING FX
        if uploaded_file or st.session_state.active_ai_image:
            st.subheader("Tuning FX (Edycja)")
            edit_model_opt = st.selectbox("Model FX ($):", ["Pro ($0.07)", "Standard ($0.02)"])
            edit_model_pure = "grok-imagine-image-pro" if "Pro" in edit_model_opt else "grok-imagine-image"
            edit_prompt = st.text_input("Zmień coś (np. red hat):", placeholder="green dress")
            if st.button("🪄 Tunuj Aktywne Źródło", use_container_width=True):
                with st.spinner("Pracuję nad obrazem..."):
                    try:
                        # 1. Priorytet ma zdjęcie AI, potem wgrane
                        source_bytes = None
                        if st.session_state.active_ai_image:
                            buf = io.BytesIO(); st.session_state.active_ai_image.save(buf, format="PNG"); source_bytes = buf.getvalue()
                        elif uploaded_file:
                            source_bytes = uploaded_file.getvalue()
                        
                        # 2. Wykonujemy Tuning
                        res = edit_image_xai(api_key, source_bytes, edit_prompt, model_name=edit_model_pure)
                        st.session_state.active_ai_image = Image.open(io.BytesIO(requests.get(res.url).content))
                        st.session_state.draft += f"[motion: high-fidelity clothing transformation to {edit_prompt}] "
                        st.success("Tuning zakończony!")
                    except Exception as e: st.error(f"Błąd FX: {e}")
        else:
            st.info("Wgraj zdjęcie lub wygeneruj je w zakładce 'Generator', aby użyć tuningu.")

    st.divider()
    # Zarządzanie draftem
    if st.button("⏪ UNDO (Cofnij krok)", use_container_width=True):
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1]); st.rerun()
    if st.button("🗑️ CZYŚĆ SCENARIUSZ", type="secondary", use_container_width=True):
        st.session_state.draft = ""; st.rerun()

# --- PANEL REŻYSERSKI 3x2 ---
# (Wyświetlamy podgląd aktywnego zdjęcia na środku)
st.divider()
col_img, col_ui = st.columns([1, 2])
with col_img:
    if st.session_state.active_ai_image:
        st.image(st.session_state.active_ai_image, caption="🆕 Aktywne źródło (AI Pro)", use_container_width=True)
    elif uploaded_file:
        st.image(Image.open(uploaded_file), caption="Z wgranego pliku", use_container_width=True)
    else:
        st.info("Wgraj zdjęcie źródłowe lub wygeneruj nową postać w pasku bocznym.")

with col_ui:
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.subheader("🎥 Kamera")
        cam_list = [
            "steady close-up on face — Portret",
            "dynamic tilt down to hips — Biodra",
            "full shot — Sylwetka",
            "over-the-shoulder — Zza ramienia",
            "dolly zoom in — Efekt Vertigo",
            "handheld shake — Realizm",
            "orbit shot — Kamera krąży",
            "dutch angle — Krzywy kadr",
            "whip pan — Szybki obrót"
        ]
        sel_cam = st.selectbox("Ujęcie:", cam_list)
        if st.button("➕ Dodaj Kamerę"):
            c_p = sel_cam.split(" — ")[0]
            st.session_state.draft += f"[camera: {c_p}] "
            if any(x in c_p for x in ["face", "close-up"]):
                st.session_state.draft += "[motion: high-fidelity facial animation, perfect lip-sync] "

    with r1c2:
        st.subheader("🎙️ Dialog")
        txt = st.text_input("Tekst mowy:", placeholder="Wojtek, zobacz moją sukienkę!")
        if st.button("➕ Dodaj Dialog"):
            if txt: st.session_state.draft += f"[voice: polish] [pause: 0.6s] \"{txt}\" [pause: 0.5s] "

    with r1c3:
        st.subheader("💃 Ruch")
        act = st.text_input("Ruch (PL):", placeholder="uśmiecha się zalotnie")
        if st.button("➕ Dodaj Ruch"):
            if act:
                with st.spinner("Tłumaczenie..."):
                    st.session_state.draft += f"{elon_translator(act, 'motion')} "

    st.divider()
    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        st.subheader("🎵 Muzyka")
        m_opt = st.selectbox("Podkład muzyczny:", ["Subtle Hip-Hop Beat", "Cinematic Tension", "Lo-Fi Chill", "Romantic Piano", "Dark Techno Pulse"])
        if st.button("➕ Audio"):
            st.session_state.draft += f"[audio: background {m_opt.lower()}] "

    with r2c2:
        st.subheader("🔊 SFX")
        s_opt = st.selectbox("Efekt SFX:", ["Crowd Applause", "Heavy Breathing", "Heartbeat Thump", " Thunder Clap", "Camera Shutter"])
        if st.button("➕ SFX"):
            st.session_state.draft += f"[audio: {s_opt.lower()}] "

    with r2c3:
        st.subheader("🎭 Głos")
        v_opt = st.selectbox("Filtr głosu:", ["Whisper — Szept", "Robot Voice", "Radio Filter", "Deep Bass Voice", "Echo Reverb"])
        if st.button("➕ Filtr"):
            st.session_state.draft += f"[audio: {v_opt.split(' — ')[0].lower()}] "

# --- DRAFT I RENDER ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=120)
est = estimate_duration(st.session_state.draft)

col_a, col_b = st.columns(2)
with col_a:
    res_opt = st.selectbox("Jakość:", ["720p", "480p"], index=0)
with col_b:
    dur = st.slider("Długość (s):", 5, 15, int(min(max(est, 5), 15)))

if st.button("🚀 WYPAL FINALNE WIDEO (HD)", type="primary", use_container_width=True):
    # Wybór zdjęcia: priorytet ma AI, potem wgrane
    img = st.session_state.active_ai_image if st.session_state.active_ai_image else (Image.open(uploaded_file) if uploaded_file else None)
    
    if img and st.session_state.draft:
        with st.spinner(f"Renderowanie w {res_opt}..."):
            # Konwersja zdjęcia na b64
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="JPEG")
            img_bytes = img_buffer.getvalue()
            b64 = base64.b64encode(img_bytes).decode()
            
            async def _gen():
                c = xai_sdk.AsyncClient(api_key=api_key)
                return await c.video.generate(model="grok-imagine-video", image_url=f"data:image/jpeg;base64,{b64}", 
                                                   prompt=st.session_state.draft, duration=dur, resolution=res_opt,
                                                   timeout=timedelta(minutes=10))
            try:
                loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); video = loop.run_until_complete(_gen())
                if video.respect_moderation:
                    v_res = requests.get(video.url).content
                    st.video(v_res); st.download_button("💾 POBIERZ KLIP", v_res, "render_v56.mp4", "video/mp4")
                else:
                    st.error("⚠️ Wideo zostało zablokowane przez filtry moderacji xAI.")
            except Exception as e: st.error(f"Błąd renderowania: {e}")
    else:
        st.error("⚠️ Brak zdjęcia źródłowego lub scenariusza!")
