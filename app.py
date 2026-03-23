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
st.set_page_config(page_title="RAWMOTION Director's Pro v4", layout="wide", page_icon="🎬")

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
    payload = {
        "model": "grok-4-1-fast-non-reasoning", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        return res.json()['choices'][0]['message']['content']
    except: return f"[{context_type}: error]"

def estimate_duration(prompt):
    pauses = re.findall(r"\[pause:\s*(\d+\.?\d*)s\]", prompt)
    pause_time = sum(float(p) for p in pauses)
    audio_tags = re.findall(r"\[audio:\s*(.*?)\]", prompt)
    audio_time = len(audio_tags) * 1.5
    clean_text = re.sub(r"\[.*?\]", "", prompt)
    words = len(clean_text.split())
    return round(pause_time + (words * 0.75) + audio_time + 3.0, 1)

# --- ZMIANA: NOWA FUNKCJA EDYCJI OBRAZU (IMAGE EDITS) ---
def edit_image_xai(api_key, img_bytes, prompt):
    """Edytuje obraz przy użyciu Grok Imagine Edits przez bezpośrednie API."""
    url = "https://api.x.ai/v1/images/edits"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    # Przygotowanie pliku do wysyłki (multipart/form-data)
    files = {
        "image": ("image.jpg", img_bytes, "image/jpeg"),
        "prompt": (None, prompt),
        "model": (None, "grok-imagine-image-pro")
    }
    
    res = requests.post(url, headers=headers, files=files)
    
    if res.status_code == 200:
        # Zakładamy, że zwraca JSON z URL (standard w xAI)
        return type('obj', (object,), {'url': res.json()['data'][0]['url']})
    else:
        raise Exception(f"Błąd API: {res.text}")

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director's Pro v4.0 (Studio FX)")

if "draft" not in st.session_state: st.session_state.draft = ""
if "ztunowane_zdjecie" not in st.session_state: st.session_state.ztunowane_zdjecie = None

st.divider()
uploaded_file = st.file_uploader("🖼️ KROK 1: Wgraj zdjęcie źródłowe:", type=['jpg','png','jpeg'])

# --- SIDEBAR: ROZBUDOWANY O TUNING AI ---
with st.sidebar:
    st.header("👤 Postać w Filmie")
    char_desc_pl = st.text_area("Opis polski (do draftu):", "Fotorealistyczna kobieta, styl kinowy")
    if st.button("➕ Wstaw Postać do Osi", use_container_width=True):
        with st.spinner("Tłumaczenie..."):
            st.session_state.draft += f"{elon_translator(char_desc_pl, 'character')} "
    
    st.divider()
    
    # === NOWA SEKCJA: TUNING ZDJĘCIA AI (IMAGE EDITS) ===
    st.subheader("🆕 Tuning Zdjęcia AI (FX)")
    tuning_mode = st.selectbox("Wybierz tryb:", ["Brak tuningu", "Stylizacja (Image-to-Image)", "Zmień element (Inpainting)"])
    
    if tuning_mode != "Brak tuningu" and uploaded_file is not None:
        tuning_prompt = st.text_input("Opisz zmianę po polsku (np. dodaj tatuaż):")
        if st.button("🛠️ Tunuj Zdjęcie", use_container_width=True):
            if tuning_prompt:
                with st.spinner("Tłumaczenie promptu i tuning zdjęcia..."):
                    try:
                        # 1. Tłumaczenie promptu edycji na angielski
                        tech_tag = elon_translator(tuning_prompt, "action")
                        clean_prompt = re.sub(r"\[.*?\]", "", tech_tag).strip() # Wyciąga sam tekst
                        
                        # 2. Wywołanie API edycji
                        img_bytes = uploaded_file.getvalue()
                        edited_res = edit_image_xai(api_key, img_bytes, clean_prompt)
                        
                        # 3. Pobranie i zapisanie ztunowanego zdjęcia
                        edited_img_data = requests.get(edited_res.url).content
                        st.session_state.ztunowane_zdjecie = Image.open(io.BytesIO(edited_img_data))
                        st.success("Zdjęcie ztunowane poprawnie!")
                    except Exception as e:
                        st.error(f"⚠️ Błąd tuningu: {e}")
            else:
                st.error("Wpisz opis zmiany!")
    elif tuning_mode != "Brak tuningu" and uploaded_file is None:
        st.warning("Najpierw wgraj zdjęcie w głównym panelu!")

    st.divider()
    
    # === WYŚWIETLANIE PODGLĄDU (WGGRANEGO LUB AI) ===
    if st.session_state.ztunowane_zdjecie:
        st.image(st.session_state.ztunowane_zdjecie, caption="🆕 Aktywne źródło (ztunowane przez AI)", use_container_width=True)
        if st.button("🗑️ Usuń tuning AI", type="secondary", use_container_width=True):
            st.session_state.ztunowane_zdjecie = None
            st.rerun()
    elif uploaded_file:
        st.image(Image.open(uploaded_file), caption="Z wgranego pliku", use_container_width=True)
    
    st.divider()
    # Zarządzanie draftem
    if st.button("⏪ COFNIJ (UNDO)", use_container_width=True):
        pattern = r"\[.*?\]\s*$"
        if re.search(pattern, st.session_state.draft.strip()):
            st.session_state.draft = re.sub(pattern, "", st.session_state.draft.strip())
        else:
            words = st.session_state.draft.strip().split()
            if words: st.session_state.draft = " ".join(words[:-1])
        st.rerun()
    if st.button("🗑️ CZYŚĆ SCENARIUSZ", type="secondary", use_container_width=True):
        st.session_state.draft = ""; st.rerun()

# --- PANEL REŻYSERSKI 3x2 ---
# (Tutaj kod pozostaje bez zmian, usuwam dla czytelności odpowiedzi)
# ... Kody kolumn r1c1, r1c2, r1c3, r2c1, r2c2, r2c3 ...

# --- DRAFT I RENDER (ZAKTUALIZOWANA LOGIKA ŹRÓDŁA) ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=120)
est_time = estimate_duration(st.session_state.draft)
st.info(f"⏱️ Szacowany czas: **{est_time}s** | 💰 Koszt: **${round(est_time*0.05, 2)}**")

r_col1, r_col2 = st.columns(2)
with r_col1:
    st.markdown("### Suwak Długości")
with r_col2:
    final_dur = st.slider("Długość filmu (s):", 5, 15, int(min(max(est_time, 5), 15)))
    if st.button("🚀 WYPAL WIDEO", type="primary", use_container_width=True):
        # NOWA LOGIKA: Sprawdza ztunowane zdjęcie lub wgrane
        active_image = st.session_state.ztunowane_zdjecie if st.session_state.ztunowane_zdjecie else (Image.open(uploaded_file) if uploaded_file else None)
        
        if active_image and st.session_state.draft:
            with st.spinner("Produkcja 'Petardy'..."):
                # Konwersja aktywnego zdjęcia na b64
                img_buffer = io.BytesIO()
                active_image.save(img_buffer, format="JPEG")
                img_bytes = img_buffer.getvalue()
                b64 = base64.b64encode(img_bytes).decode()
                
                # Reszta renderu bez zmian
                w, h = active_image.size
                ratio = "16:9" if w/h > 1.2 else "9:16" if w/h < 0.8 else "1:1"
                async def _gen():
                    client = xai_sdk.AsyncClient(api_key=api_key)
                    return await client.video.generate(model="grok-imagine-video", image_url=f"data:image/jpeg;base64,{b64}", 
                                                       prompt=st.session_state.draft, duration=final_dur, aspect_ratio=ratio)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                video = loop.run_until_complete(_gen())
                v_res = requests.get(video.url).content
                st.video(v_res)
                st.download_button("💾 POBIERZ KLIP", v_res, "final_render.mp4", "video/mp4")
        else:
            st.error("Wgraj zdjęcie i zbuduj scenariusz!")
