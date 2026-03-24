import streamlit as st
import xai_sdk
import asyncio
import base64
import requests
import io
from PIL import Image

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION Director v7.8", layout="wide", page_icon="🎬")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔐 Director's Entrance")
        pwd = st.text_input("Hasło:", type="password")
        if st.button("Wejdź"):
            if pwd == st.secrets["MY_APP_PASSWORD"]:
                st.session_state["authenticated"] = True; st.rerun()
            else: st.error("Błędne hasło.")
        return False
    return True

if not check_password(): st.stop()

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
st.title("🎥 RAWMOTION Director v7.8 (Reference Mode)")

if "draft" not in st.session_state: st.session_state.draft = ""

with st.sidebar:
    st.header("👥 Obsada")
    mode = st.radio("Tryb:", ["Solo", "Duo"])
    up_a = st.file_uploader("Zdjęcie 1 (<IMAGE_1>):", type=['jpg','png','jpeg'])
    up_b = st.file_uploader("Zdjęcie 2 (<IMAGE_2>):", type=['jpg','png','jpeg']) if mode == "Duo" else None
    
    st.divider()
    if st.button("➕ Dodaj Postać A do promptu"):
        st.session_state.draft += "The person from <IMAGE_1> "
    if mode == "Duo" and st.button("➕ Dodaj Postać B do promptu"):
        st.session_state.draft += "The person from <IMAGE_2> "
    
    st.divider()
    if st.button("🗑️ CZYŚĆ DRAFT"): st.session_state.draft = ""; st.rerun()

# PANEL REŻYSERSKI 3x2
col_img, col_ui = st.columns([1, 2])
with col_img:
    if up_a: st.image(up_a, caption="IMAGE_1", use_container_width=True)
    if up_b: st.image(up_b, caption="IMAGE_2", use_container_width=True)

with col_ui:
    c1, c2, c3 = st.columns(3)
    with c1:
        cam = st.selectbox("🎥 Kamera:", ["steady close-up", "orbit shot", "handheld shake", "whip pan"])
        if st.button("➕ Kamera"): st.session_state.draft += f"[camera: {cam}] "
    with c2:
        txt = st.text_input("🎙️ Dialog:")
        if st.button("➕ Dialog"): st.session_state.draft += f"[voice: polish] \"{txt}\" [pause: 0.5s] "
    with c3:
        act = st.text_input("💃 Ruch (PL):")
        if st.button("➕ Ruch"): st.session_state.draft += f"{elon_translator(act, 'motion')} "

# --- RENDER (Official Reference Logic) ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (Pamiętaj o użyciu <IMAGE_1> i <IMAGE_2>):", value=st.session_state.draft, height=150)
q = st.selectbox("Jakość:", ["480p", "720p"])
d = st.slider("Długość (max 10s dla Reference):", 5, 10, 10)

if st.button("🚀 WYPAL FINALNE WIDEO", type="primary", use_container_width=True):
    if not up_a or (mode == "Duo" and not up_b): st.error("Wgraj zdjęcia!"); st.stop()
    
    with st.spinner("Wypalanie z referencją..."):
        try:
            # Przygotowanie obrazów jako data URI
            refs = [f"data:image/jpeg;base64,{base64.b64encode(up_a.getvalue()).decode()}"]
            if mode == "Duo":
                refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_b.getvalue()).decode()}")
            
            # Używamy SDK Elona z poprawnymi parametrami
            client = xai_sdk.Client(api_key=api_key)
            response = client.video.generate(
                model="grok-imagine-video",
                prompt=st.session_state.draft,
                reference_image_urls=refs,
                duration=d,
                resolution=q,
                aspect_ratio="16:9"
            )
            
            st.video(requests.get(response.url).content)
            st.success("🎬 Akcja! Render kompletny.")
        except Exception as e:
            st.error(f"🔴 Błąd: {str(e)}")
