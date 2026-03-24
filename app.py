import streamlit as st
import base64
import requests
import json
from PIL import Image
import io
from datetime import timedelta

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION Director v7.6", layout="wide", page_icon="🎬")

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

# --- 2. LOGIC & DIRECT API ---
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

def generate_image_direct(api_key, prompt):
    url = "https://api.x.ai/v1/images/samplings"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "grok-imagine-image-pro", "prompt": prompt, "aspect_ratio": "1:1"}
    res = requests.post(url, headers=headers, json=payload)
    return res.json()['url']

def edit_image_direct(api_key, img_bytes, prompt):
    url = "https://api.x.ai/v1/images/edits"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    uri = f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode('utf-8')}"
    payload = {"model": "grok-imagine-image-pro", "prompt": prompt, "image_url": uri}
    res = requests.post(url, headers=headers, json=payload)
    return res.json()['data'][0]['url']

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v7.6 (Full Studio)")

if "draft" not in st.session_state: st.session_state.draft = ""
if "active_ai_source" not in st.session_state: st.session_state.active_ai_source = None

# --- SIDEBAR: PEŁNE ZARZĄDZANIE ---
with st.sidebar:
    mode = st.radio("🎬 Tryb Obsady:", ["Solo (1 Osoba / AI)", "Duo (2 Osoby - Direct)"])
    st.divider()

    if mode == "Solo (1 Osoba / AI)":
        st.subheader("👤 Postać Solo")
        up_file = st.file_uploader("Wgraj zdjęcie:", type=['jpg','png','jpeg'])
        if up_file:
            desc_pl = st.text_input("Opisz postać (PL):", "Fotorealistyczna kobieta")
            if st.button("➕ Wstaw [character]", use_container_width=True):
                st.session_state.draft += f"{elon_translator(desc_pl, 'character')} "
        st.divider()
        st.subheader("✨ Generator AI")
        gen_p = st.text_input("Kogo stworzyć?")
        if st.button("🚀 Generuj AI", use_container_width=True):
            with st.spinner("Grok tworzy..."):
                url = generate_image_direct(api_key, gen_p)
                st.session_state.active_ai_source = Image.open(io.BytesIO(requests.get(url).content))
                st.session_state.draft += f"{elon_translator(gen_p, 'character')} "
        st.divider()
        st.subheader("🛠️ Tuning FX")
        if up_file or st.session_state.active_ai_source:
            edit_p = st.text_input("Zmiana (np. red dress):")
            if st.button("🪄 Wykonaj Tuning", use_container_width=True):
                with st.spinner("Edytuję..."):
                    src = up_file.getvalue() if up_file else None
                    if not src:
                        buf = io.BytesIO(); st.session_state.active_ai_source.save(buf, format="PNG"); src = buf.getvalue()
                    url = edit_image_direct(api_key, src, edit_p)
                    st.session_state.active_ai_source = Image.open(io.BytesIO(requests.get(url).content))
                    st.session_state.draft += f"[motion: transformation to {edit_p}] "
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
    if st.button("🗑️ CZYŚĆ"):
        st.session_state.draft = ""; st.session_state.active_ai_source = None; st.rerun()

# --- PANEL REŻYSERSKI 3x2 ---
st.subheader("🖼️ Podgląd")
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
        st.subheader("🎥 Kamera")
        cam = st.selectbox("Ujęcie:", ["steady close-up", "tilt down", "full shot", "dolly zoom", "orbit shot", "handheld shake", "whip pan", "dutch angle"])
        if st.button("➕ Kamera"): st.session_state.draft += f"[camera: {cam}] "
    with r1c2:
        st.subheader("🎙️ Dialog")
        txt = st.text_input("Tekst:")
        spk = st.selectbox("Mówi:", ["Osoba A", "Osoba B"]) if mode == "Duo (2 Osoby - Direct)" else None
        if st.button("➕ Dialog"):
            tag = f" person {spk[-1]}" if spk else ""
            st.session_state.draft += f"[voice: polish{tag}] \"{txt}\" [pause: 0.5s] "
    with r1c3:
        st.subheader("💃 Ruch")
        act = st.text_input("Akcja (PL):")
        if st.button("➕ Ruch"): st.session_state.draft += f"{elon_translator(act, 'motion')} "

    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        st.subheader("🎵 Muzyka")
        m_opt = st.selectbox("Styl:", ["Hip-Hop", "Cinematic", "Lo-Fi", "Romantic", "Techno", "Dark Synth"])
        if st.button("➕ Audio"): st.session_state.draft += f"[audio: background {m_opt.lower()}] "
    with r2c2:
        st.subheader("🔊 SFX")
        s_opt = st.selectbox("Efekt:", ["Applause", "Heartbeat", "Thunder", "Shutter", "Scream", "Door burst"])
        if st.button("➕ SFX"): st.session_state.draft += f"[audio: {s_opt.lower()}] "
    with r2c3:
        st.subheader("🎭 Głos")
        v_opt = st.selectbox("Filtr:", ["Whisper", "Radio", "Echo", "Deep Bass", "Robot"])
        if st.button("➕ Filtr"): st.session_state.draft += f"[audio: {v_opt.lower()}] "

# --- RENDER (Direct) ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=150)
col_q, col_d = st.columns(2)
with col_q: q = st.selectbox("Jakość:", ["480p", "720p"])
with col_d: d = st.slider("Długość (s):", 5, 15, 10)

if st.button("🚀 WYPAL FINALNE WIDEO", type="primary", use_container_width=True):
    if not st.session_state.draft: st.error("Wklej prompt!"); st.stop()
    with st.spinner("Łączenie z serwerem xAI..."):
        try:
            # Przygotowanie obrazów
            if mode == "Solo (1 Osoba / AI)":
                imgs = [base64.b64encode(io.BytesIO(requests.get(generate_image_direct(api_key, "temp")).content).getvalue()).decode()] # placeholder
                if st.session_state.active_ai_source:
                    buf = io.BytesIO(); st.session_state.active_ai_source.save(buf, format="JPEG"); imgs = [base64.b64encode(buf.getvalue()).decode()]
                elif up_file: imgs = [base64.b64encode(up_file.getvalue()).decode()]
            else:
                imgs = [base64.b64encode(up_a.getvalue()).decode(), base64.b64encode(up_b.getvalue()).decode()]

            # WYSYŁKA DIRECT
            url = "https://api.x.ai/v1/video/generations"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            image_urls = [f"data:image/jpeg;base64,{b64}" for b64 in imgs]
            payload = {
                "model": "grok-imagine-video",
                "image_url": image_urls if len(image_urls) > 1 else image_urls[0],
                "prompt": st.session_state.draft,
                "duration": d,
                "resolution": q
            }
            res = requests.post(url, headers=headers, json=payload, timeout=600)
            if res.status_code == 200: st.video(res.json()['url']); st.success("🎬 Akcja!")
            else: st.error(f"Błąd API {res.status_code}: {res.text}")
        except Exception as e: st.error(f"🔴 Krytyczny błąd: {str(e)}")
