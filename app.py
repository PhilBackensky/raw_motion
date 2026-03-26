import streamlit as st
import xai_sdk
import asyncio
import base64
import requests
import io
from PIL import Image
from datetime import timedelta

# --- 1. CONFIG & SECURITY (v8.3) ---
st.set_page_config(page_title="RAWMOTION v8.3", layout="wide", page_icon="🎬")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    pwd = st.text_input("Hasło wejścia:", type="password")
    if st.button("Wejdź"):
        if pwd == st.secrets["MY_APP_PASSWORD"]:
            st.session_state["authenticated"] = True; st.rerun()
        else: st.error("Błędne hasło.")
    st.stop()

# --- 2. LOGIC ---
api_key = st.secrets["XAI_API_KEY"]

def elon_translator(text, context_type):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    tag = "[character: ...]" if context_type == "character" else "[motion: ...]"
    prompt = f"Translate to technical tag for Memphis engine using {tag}. Output ONLY tag. Text: {text}"
    payload = {"model": "grok-4-1-fast-non-reasoning", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    try:
        res = requests.post(url, headers=headers, json=payload)
        return res.json()['choices'][0]['message']['content']
    except: return f"[{context_type}: error]"

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v8.3 (Stereo Fix)")
if "draft" not in st.session_state: st.session_state.draft = ""

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Studio Setup")
    mode = st.radio("Tryb:", ["Solo / Edit", "Duo / Interactions", "Trio / Selfie"])
    st.divider()
    
    up_1 = st.file_uploader("Osoba 1 (<IMAGE_1>):", type=['jpg','png','jpeg'])
    up_2 = st.file_uploader("Osoba 2 (<IMAGE_2>):", type=['jpg','png','jpeg']) if "Duo" in mode or "Trio" in mode else None
    up_3 = st.file_uploader("Osoba 3 (<IMAGE_3>):", type=['jpg','png','jpeg']) if "Trio" in mode else None

    if st.button("✨ Resetuj Draft"): st.session_state.draft = ""; st.rerun()
    if st.button("⏪ Undo"): 
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1]); st.rerun()

# --- PANEL REŻYSERSKI 3x2 ---
st.subheader("🖼️ Panel Kontrolny")
col_img, col_ui = st.columns([1, 2])

with col_img:
    c1, c2 = st.columns(2)
    with c1: 
        if up_1: st.image(up_1, caption="IMAGE_1 (Lewa)", use_container_width=True)
    with c2: 
        if up_2: st.image(up_2, caption="IMAGE_2 (Prawa)", use_container_width=True)
    if up_3: st.image(up_3, caption="IMAGE_3", use_container_width=True)

with col_ui:
    # Rząd 1
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("🎥 **Kamera**")
            cam = st.selectbox("Ujęcie:", ["steady close-up", "orbit 360", "handheld shake", "whip pan", "dolly zoom"])
            if st.button("➕ Kamera"): st.session_state.draft += f"[camera: {cam}] "
        with c2:
            st.write("🎙️ **Stereo Dialog (v8.3)**")
            txt = st.text_input("Tekst:")
            who = st.selectbox("Mówi:", ["Osoba 1 (Lewa)", "Osoba 2 (Prawa)", "Osoba 3"])
            if st.button("➕ Dialog"):
                tag = who[-1]
                pos = "left" if tag == "1" else "right"
                # Dodajemy ścisłe Audio Panning do tagu [voice]
                st.session_state.draft += f"[voice: polish person {tag} on the {pos}] \"{txt}\" [pause: 1.0s] "
        with c3:
            st.write("🕺 **Interakcja**")
            inter = st.selectbox("Akcja:", ["patrzą na siebie", "obejmują się", "kłócą się", "dziubek do selfie"])
            if st.button("➕ Interakcja"):
                st.session_state.draft += f"[motion: high-fidelity facial interaction between characters, {inter}] "

    st.write("") # Odstęp

    # Rząd 2
    with st.container():
        c4, c5, c6 = st.columns(3)
        with c4:
            st.write("🎵 **Muzyka**")
            mus = st.selectbox("Styl:", ["Cinematic", "Hip-Hop", "Techno", "Romantic"])
            if st.button("➕ Audio"): st.session_state.draft += f"[audio: background {mus.lower()}] "
        with c5:
            st.write("🔊 **SFX**")
            sfx = st.selectbox("Efekt:", ["Applause", "Laughter", "Thunder", "Scream"])
            if st.button("➕ SFX"): st.session_state.draft += f"[audio: {sfx.lower()}] "
        with c6:
            st.write("🎭 **Filtry**")
            fil = st.selectbox("Filtr:", ["Whisper", "Radio", "Echo", "Robot"])
            if st.button("➕ Filtr"): st.session_state.draft += f"[audio: {fil.lower()}] "

# --- RENDER ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=120)

col_q, col_d = st.columns(2)
with col_q: res = st.selectbox("Jakość:", ["480p", "720p"], index=1) # Domyślnie 720p
with col_d: dur = st.slider("Długość (s):", 5, 10, 10)

if st.button("🚀 WYPAL FINALNE WIDEO", type="primary", use_container_width=True):
    if not up_1: st.error("Wgraj zdjęcie!"); st.stop()
    with st.spinner("Synchronizacja Stereo Logic i renderowanie..."):
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            client = xai_sdk.AsyncClient(api_key=api_key)
            
            refs = [f"data:image/jpeg;base64,{base64.b64encode(up_1.getvalue()).decode()}"]
            if up_2: refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_2.getvalue()).decode()}")
            if up_3: refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_3.getvalue()).decode()}")
            
            # NOWY PREFIX V8.3 (Ścisłe pozycjonowanie przestrzenne)
            prefix = "[character: <IMAGE_1> is person 1 on the left"
            if up_2: prefix += ", <IMAGE_2> is person 2 on the right"
            if up_3: prefix += ", <IMAGE_3> is person 3"
            prefix += "]. "
            
            final_p = prefix + st.session_state.draft
            
            async def render():
                return await client.video.generate(
                    model="grok-imagine-video",
                    prompt=final_p,
                    reference_image_urls=refs,
                    duration=dur,
                    resolution=res,
                    aspect_ratio="16:9"
                )

            v_res = loop.run_until_complete(render())
            st.video(requests.get(v_res.url).content)
            st.success("✅ Stereo Sync wypalony pomyślnie!")
        except Exception as e: st.error(f"🔴 Błąd: {str(e)}")
