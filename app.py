import streamlit as st
import xai_sdk
import asyncio
import base64
import requests
import io
from PIL import Image
from datetime import timedelta

# --- 1. KONFIGURACJA I BEZPIECZEŃSTWO ---
st.set_page_config(page_title="RAWMOTION Trio v8.0", layout="wide", page_icon="🎬")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 Director's Entrance")
    pwd = st.text_input("Hasło wejścia:", type="password")
    if st.button("Wejdź"):
        if pwd == st.secrets["MY_APP_PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Błędne hasło.")
    st.stop()

# --- 2. LOGIKA TRANSLACJI ---
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
    except:
        return f"[{context_type}: error]"

# --- 3. INTERFEJS UŻYTKOWNIKA ---
st.title("🎥 RAWMOTION Director v8.0 (Trio & Selfie Mode)")
if "draft" not in st.session_state:
    st.session_state.draft = ""

# --- SIDEBAR: OBSADA ---
with st.sidebar:
    st.header("👥 Obsada (Trio)")
    up_1 = st.file_uploader("RAFAŁ (<IMAGE_1>):", type=['jpg','png','jpeg'])
    up_2 = st.file_uploader("DZIEWCZYNA 1 (<IMAGE_2>):", type=['jpg','png','jpeg'])
    up_3 = st.file_uploader("DZIEWCZYNA 2 (<IMAGE_3>):", type=['jpg','png','jpeg'])
    
    st.divider()
    if st.button("➕ Dodaj Rafała do sceny"):
        st.session_state.draft += "The person from <IMAGE_1> "
    if st.button("➕ Dodaj Dziewczynę 1"):
        st.session_state.draft += "The person from <IMAGE_2> "
    if st.button("➕ Dodaj Dziewczynę 2"):
        st.session_state.draft += "The person from <IMAGE_3> "
    
    st.divider()
    if st.button("⏪ UNDO"):
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1])
        st.rerun()
    if st.button("🗑️ CZYŚĆ WSZYSTKO", type="secondary"):
        st.session_state.draft = ""
        st.rerun()

# --- PANEL PODGLĄDU I REŻYSERII ---
col_img, col_ui = st.columns([1, 2])
with col_img:
    if up_1: st.image(up_1, caption="REF 1 (Rafał)", use_container_width=True)
    if up_2: st.image(up_2, caption="REF 2", use_container_width=True)
    if up_3: st.image(up_3, caption="REF 3", use_container_width=True)

with col_ui:
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.subheader("🎥 Kamera")
        cam = st.selectbox("Styl:", ["handheld selfie shake", "360 orbit rotate", "steady close-up", "whip pan"])
        if st.button("➕ Kamera"): st.session_state.draft += f"[camera: {cam}] "
    with r1c2:
        st.subheader("🎙️ Dialog")
        txt = st.text_input("Co mówią?")
        spk = st.selectbox("Kto mówi:", ["Dziewczyna 1", "Dziewczyna 2", "Rafał"])
        if st.button("➕ Dialog"):
            # Mapowanie na tagi person zgodne z IMAGE_N
            who = "person 2" if "1" in spk else ("person 3" if "2" in spk else "person 1")
            st.session_state.draft += f"[voice: polish {who}] \"{txt}\" [pause: 0.5s] "
    with r1c3:
        st.subheader("💃 Ruch")
        act = st.text_input("Akcja (PL):")
        if st.button("➕ Ruch"):
            st.session_state.draft += f"{elon_translator(act, 'motion')} "

# --- SEKCJA RENDEROWANIA ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=150)

col_q, col_d = st.columns(2)
with col_q:
    res_opt = st.selectbox("Jakość:", ["480p", "720p"], index=0)
with col_d:
    dur = st.slider("Długość (max 10s dla Reference):", 5, 10, 10)

if st.button("🚀 WYPAL TRIO-SELFIE", type="primary", use_container_width=True):
    if not (up_1 and up_2 and up_3):
        st.error("⚠️ Do trybu Trio potrzebujesz wgrać wszystkie 3 zdjęcia!"); st.stop()
    
    with st.spinner("Inicjacja silnika Memphis... To potrwa moment."):
        try:
            # Tworzenie pętli zdarzeń dla bezpiecznego Async w Streamlit
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            client = xai_sdk.AsyncClient(api_key=api_key)
            
            # Kodowanie obrazów do base64
            refs = [
                f"data:image/jpeg;base64,{base64.b64encode(up_1.getvalue()).decode()}",
                f"data:image/jpeg;base64,{base64.b64encode(up_2.getvalue()).decode()}",
                f"data:image/jpeg;base64,{base64.b64encode(up_3.getvalue()).decode()}"
            ]
            
            async def start_render():
                return await client.video.generate(
                    model="grok-imagine-video",
                    prompt=st.session_state.draft,
                    reference_image_urls=refs,
                    duration=dur,
                    resolution=res_opt,
                    aspect_ratio="16:9",
                    timeout=timedelta(minutes=15)
                )

            res_video = loop.run_until_complete(start_render())
            st.video(requests.get(res_video.url).content)
            st.success("🎬 Akcja! Wideo wygenerowane pomyślnie.")
            
        except Exception as e:
            st.error(f"🔴 Błąd Trio: {str(e)}")
