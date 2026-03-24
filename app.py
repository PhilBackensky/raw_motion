import streamlit as st
import base64
import requests
import json
from PIL import Image
import io

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION Director v7.7", layout="wide", page_icon="🎬")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔐 Director's Entrance")
        try: correct_password = st.secrets["MY_APP_PASSWORD"]
        except: st.error("Błąd: Brak hasła w Secrets!"); st.stop()
        pwd = st.text_input("Hasło:", type="password")
        if st.button("Wejdź"):
            if pwd == correct_password: st.session_state["authenticated"] = True; st.rerun()
            else: st.error("Błędne hasło.")
        return False
    return True

if not check_password(): st.stop()

# --- 2. LOGIC & API ---
api_key = st.secrets["XAI_API_KEY"]
BASE_URL = "https://api.x.ai/v1/images/samplings" # Poprawny punkt dla Grok Imagine

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
st.title("🎥 RAWMOTION Director v7.7 (The Final Link)")

if "draft" not in st.session_state: st.session_state.draft = ""
if "active_ai_source" not in st.session_state: st.session_state.active_ai_source = None

# --- SIDEBAR: PEŁNE MENU ---
with st.sidebar:
    mode = st.radio("🎬 Tryb Obsady:", ["Solo (1 Osoba / AI)", "Duo (2 Osoby - Direct)"])
    st.divider()

    if mode == "Solo (1 Osoba / AI)":
        st.subheader("👤 Zarządzanie Solo")
        up_file = st.file_uploader("Wgraj zdjęcie:", type=['jpg','png','jpeg'])
        if up_file:
            desc_pl = st.text_input("Opisz postać (PL):", "Fotorealistyczna postać")
            if st.button("➕ Wstaw [character]", use_container_width=True):
                st.session_state.draft += f"{elon_translator(desc_pl, 'character')} "
        st.divider()
        st.subheader("✨ Generator AI")
        gen_p = st.text_input("Kogo stworzyć?")
        if st.button("🚀 Generuj AI", use_container_width=True):
            with st.spinner("Grok tworzy..."):
                payload = {"model": "grok-imagine-image-pro", "prompt": gen_p, "aspect_ratio": "1:1"}
                res = requests.post(BASE_URL, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
                st.session_state.active_ai_source = Image.open(io.BytesIO(requests.get(res.json()['url']).content))
                st.session_state.draft += f"{elon_translator(gen_p, 'character')} "
    else:
        st.subheader("👥 Duo Direct")
        up_a = st.file_uploader("Zdjęcie A (Postać A):", type=['jpg','png','jpeg'])
        up_b = st.file_uploader("Zdjęcie B (Postać B):", type=['jpg','png','jpeg'])
        if up_a:
            if st.button("➕ Wstaw Postać A", use_container_width=True):
                st.session_state.draft += "[character: Person A from Image 1] "
        if up_b:
            if st.button("➕ Wstaw Postać B", use_container_width=True):
                st.session_state.draft += "[character: Person B from Image 2] "

    st.divider()
    if st.button("⏪ UNDO"):
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1]); st.rerun()

# --- PANEL REŻYSERSKI 3x2 ---
col_img, col_ui = st.columns([1, 2])
with col_img:
    if mode == "Solo (1 Osoba / AI)":
        disp = st.session_state.active_ai_source if st.session_state.active_ai_source else (Image.open(up_file) if "up_file" in locals() and up_file else None)
        if disp: st.image(disp, use_container_width=True)
    else:
        c1, c2 = st.columns(2)
        with c1: 
            if up_a: st.image(Image.open(up_a), caption="A", use_container_width=True)
        with c2: 
            if up_b: st.image(Image.open(up_b), caption="B", use_container_width=True)

with col_ui:
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        cam = st.selectbox("🎥 Kamera:", ["steady close-up", "tilt down", "full shot", "dolly zoom", "orbit shot", "handheld shake", "whip pan"])
        if st.button("➕ Kamera"): st.session_state.draft += f"[camera: {cam}] "
    with r1c2:
        txt = st.text_input("🎙️ Tekst:")
        spk = st.selectbox("Mówi:", ["Osoba A", "Osoba B"]) if mode == "Duo (2 Osoby - Direct)" else None
        if st.button("➕ Dialog"):
            tag = f" person {spk[-1]}" if spk else ""
            st.session_state.draft += f"[voice: polish{tag}] \"{txt}\" [pause: 0.5s] "
    with r1c3:
        act = st.text_input("💃 Ruch:")
        if st.button("➕ Ruch"): st.session_state.draft += f"{elon_translator(act, 'motion')} "
    
    # MUZYKA I SFX
    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        m = st.selectbox("🎵 Muzyka:", ["Hip-Hop", "Cinematic", "Techno"])
        if st.button("➕ Audio"): st.session_state.draft += f"[audio: background {m.lower()}] "
    with r2c2:
        s = st.selectbox("🔊 SFX:", ["Applause", "Thunder", "Scream"])
        if st.button("➕ SFX"): st.session_state.draft += f"[audio: {s.lower()}] "
    with r2c3:
        v = st.selectbox("🎭 Głos:", ["Whisper", "Radio", "Robot"])
        if st.button("➕ Filtr"): st.session_state.draft += f"[audio: {v.lower()}] "

# --- RENDER (The Console Fix) ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=150)
col_q, col_d = st.columns(2)
with col_q: q = st.selectbox("Jakość:", ["480p", "720p"])
with col_d: d = st.slider("Długość (s):", 5, 15, 10)

if st.button("🚀 WYPAL FINALNE WIDEO", type="primary", use_container_width=True):
    with st.spinner("Łączenie z serwerem xAI (v7.7)..."):
        try:
            imgs = []
            if mode == "Solo (1 Osoba / AI)":
                if st.session_state.active_ai_source:
                    buf = io.BytesIO(); st.session_state.active_ai_source.save(buf, format="JPEG"); imgs = [base64.b64encode(buf.getvalue()).decode()]
                elif up_file: imgs = [base64.b64encode(up_file.getvalue()).decode()]
            else:
                imgs = [base64.b64encode(up_a.getvalue()).decode(), base64.b64encode(up_b.getvalue()).decode()]

            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "grok-imagine-video",
                "image_url": [f"data:image/jpeg;base64,{b}" for b in imgs] if len(imgs) > 1 else f"data:image/jpeg;base64,{imgs[0]}",
                "prompt": st.session_state.draft,
                "duration": d,
                "resolution": q
            }
            res = requests.post(BASE_URL, headers=headers, json=payload)
            if res.status_code == 200: st.video(res.json()['url']); st.success("🎬 Akcja!")
            else: st.error(f"Błąd {res.status_code}: {res.text}")
        except Exception as e: st.error(f"🔴 Błąd: {str(e)}")
