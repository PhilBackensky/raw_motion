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
st.set_page_config(page_title="RAWMOTION Duo-Director v5.9", layout="wide", page_icon="🎬")

# --- CUSTOM CSS DLA SMARTFONÓW ---
st.markdown("""
    <style>
    /* Wymuszenie siatki dla kolumn na mobilkach */
    @media (max-width: 768px) {
        [data-testid="column"] {
            width: 48% !important;
            flex: 1 1 48% !important;
            min-width: 48% !important;
            display: inline-block !important;
        }
        div[data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: wrap !important;
        }
        .stButton button {
            width: 100% !important;
            padding: 0.2rem !important;
            font-size: 12px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔐 Duo-Director Entrance")
        try: correct_password = st.secrets["MY_APP_PASSWORD"]
        except: st.error("Błąd Secrets!"); st.stop()
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
    prompt = f"Translate to technical tag for Memphis engine using {tag_format}. Output ONLY tag. Text: {text}"
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

# NOWA FUNKCJA API: FUZJA DWÓCH ZDJĘĆ
def fuse_images_xai(api_key, img_a_bytes, img_b_bytes, prompt, model_name="grok-imagine-image-pro"):
    """Fuzja dwóch zdjęć przy użyciu oficjalnego standardu Duo-URI (JSON)."""
    url = "https://api.x.ai/v1/images/edits"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 1. Kodowanie obu zdjęć do base64 z nagłówkami MIME
    img_a_b64 = base64.b64encode(img_a_bytes).decode('utf-8')
    data_uri_a = f"data:image/jpeg;base64,{img_a_b64}"
    
    img_b_b64 = base64.b64encode(img_b_bytes).decode('utf-8')
    data_uri_b = f"data:image/jpeg;base64,{img_b_b64}"
    
    # 2. Tworzymy listę zdjęć źródłowych (oficjalna składnia Duo-Editing)
    payload = {
        "model": model_name,
        "images": [data_uri_a, data_uri_b], # Przesyłamy listę Duo-URI
        "prompt": prompt,
        "aspect_ratio": "16:9" # Najlepsze do wspólnych planów
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=90)
        if res.status_code == 200:
            return res.json()['data'][0]['url']
        else:
            raise Exception(f"Błąd Duo-API {res.status_code}: {res.text}")
    except requests.exceptions.Timeout:
        raise Exception("Upłynął czas fuzji (API xAI jest powolne przy dwóch zdjęciach).")

def estimate_duration(prompt):
    words = len(re.sub(r"\[.*?\]", "", prompt).split())
    return round(words * 0.8 + 4.0, 1)

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Duo-Director v5.9")

if "draft" not in st.session_state: st.session_state.draft = ""
if "active_fused_image" not in st.session_state: st.session_state.active_fused_image = None
if "uploaded_a" not in st.session_state: st.session_state.uploaded_a = None
if "uploaded_b" not in st.session_state: st.session_state.uploaded_b = None

st.divider()

# --- SIDEBAR: DUO-ZARZĄDZANIE ---
with st.sidebar:
    st.header("👤 Zarządzanie Duo")
    
    # === SLOT A (Osoba A) ===
    st.subheader("1. Slot A (Osoba ze zdjęcia 1)")
    uploaded_a = st.file_uploader("Wgraj Osoba A:", type=['jpg','png','jpeg'])
    if uploaded_a:
        char_a_desc_pl = st.text_input("Opisz Osoba A (PL):", "Fotorealistyczna kobieta")
        if st.button("➕ Wstaw [character: A]", use_container_width=True):
            with st.spinner("Tłumaczenie A..."):
                tag_a = elon_translator(char_a_desc_pl, 'character')
                st.session_state.draft += f"{tag_a} "

    st.divider()

    # === SLOT B (Osoba B) ===
    st.subheader("2. Slot B (Osoba ze zdjęcia 2)")
    uploaded_b = st.file_uploader("Wgraj Osoba B:", type=['jpg','png','jpeg'])
    if uploaded_b:
        char_b_desc_pl = st.text_input("Opisz Osoba B (PL):", "Fotorealistyczny mężczyzna")
        if st.button("➕ Wstaw [character: B]", use_container_width=True):
            with st.spinner("Tłumaczenie B..."):
                tag_b = elon_translator(char_b_desc_pl, 'character')
                # Memphis lubi wyraźne oddzielenie postaci w drafcie
                st.session_state.draft += f"{tag_b} "
    
    st.divider()
    
    # === DUO-TUNING FX (Fuzja) ===
    if uploaded_a and uploaded_b:
        st.subheader("🛠️ Duo-Tuning FX (Fuzja)")
        gen_prompt_pl = st.text_input("Opisz ich interakcję (PL):", placeholder="hug on a beach, photorealistic")
        if st.button("🪄 Wykonaj Duo-FX (Fuzja)", use_container_width=True):
            if gen_prompt_pl:
                with st.spinner("Grok wykonuje fuzję postaci... Może to zająć do 2 minut."):
                    try:
                        # 1. Tłumaczymy opis fuzji
                        translated_gen = elon_translator(gen_prompt_pl, "action")
                        # 2. Wywołujemy Duo-API Fuzji
                        img_url = fuse_images_xai(api_key, uploaded_a.getvalue(), uploaded_b.getvalue(), translated_gen)
                        # 3. Pobieramy wynik fuzji
                        img_bytes = requests.get(img_url).content
                        st.session_state.active_fused_image = Image.open(io.BytesIO(img_bytes))
                        
                        # 4. Automatycznie dodajemy FX do draftu
                        st.session_state.draft += f"[motion: high-fidelity interaction transformation from separate photos {translated_gen}] "
                        st.success("Fuzja zakońzona! Wspólne zdjęcie jest aktywne.")
                    except Exception as e:
                        st.error(f"⚠️ Błąd Duo-FX: {e}")
            else:
                st.error("Opisz, co te dwie osoby mają robić razem!")
    else:
        st.info("Wgraj oba zdjęcia (Osoba A i B), aby użyć Duo-Tuningu.")

    st.divider()
    if st.button("⏪ UNDO", use_container_width=True):
        st.session_state.draft = " ".join(st.session_state.draft.strip().split()[:-1]); st.rerun()
    if st.button("🗑️ CZYŚĆ SCENARIUSZ", type="secondary", use_container_width=True):
        st.session_state.draft = ""; st.session_state.active_fused_image = None; st.rerun()

# --- PANEL REŻYSERSKI 3x2 ---
st.divider()
st.subheader("🖼️ Podgląd Aktywnego Źródła (Duo)")
col_img, col_ui = st.columns([1, 2])
with col_img:
    # Wyświetlamy fuzję, jeśli istnieje, w przeciwnym razie oba wgrane
    if st.session_state.active_fused_image:
        st.image(st.session_state.active_fused_image, caption="🆕 Wynik Fuzji Duo-FX", use_container_width=True)
    elif uploaded_a or uploaded_b:
        col_a, col_b = st.columns(2)
        with col_a: 
            if uploaded_a: st.image(Image.open(uploaded_a), caption="Osoba A", use_container_width=True)
        with col_b: 
            if uploaded_b: st.image(Image.open(uploaded_b), caption="Osoba B", use_container_width=True)
    else:
        st.info("Wgraj oba zdjęcia, aby zobaczyć ich wspólny plan.")

with col_ui:
    # PANEL RESPONSYWNY (Używamy siatki 2x2 z CSS dla mobilnych)
    st.subheader("🎬 Reżyseria (Interakcja)")
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        st.subheader("🎥 Kamera")
        cam_list = [
            "medium shot — Wspólny plan średni",
            "steady close-up on both faces — Twarze Duo",
            "orbit shot — Kamera krąży wokół nich",
            "over-the-shoulder A — Zza ramienia A",
            "full shot — Obie sylwetki"
        ]
        sel_cam = st.selectbox("Ujęcie:", cam_list, label_visibility="collapsed")
        if st.button("➕ Kamera"):
            c_p = sel_cam.split(" — ")[0]
            st.session_state.draft += f"[camera: {c_p}] "

    with r1c2:
        st.subheader("💃 Ruch (Duo)")
        act_pl = st.text_input("Ruch (PL):", placeholder="podają sobie dłonie...", label_visibility="collapsed")
        if st.button("➕ Ruch Duo"):
            if act_pl:
                with st.spinner("Tłumaczenie ruchu..."):
                    # Tłumaczymy ruch na tag [motion]
                    st.session_state.draft += f"{elon_translator(act_pl, 'motion')} "

    st.divider()
    
    st.subheader("🎙️ Dialog Duo (Kto mówi?)")
    txt_duo = st.text_input("Tekst mowy:", placeholder="Wojtek, zobacz...", label_visibility="collapsed")
    speaker = st.selectbox("Kto mówi:", ["Osoba A", "Osoba B"], label_visibility="collapsed")
    if st.button("➕ Dodaj Dialog Duo"):
        if txt_duo:
            sp = "person A" if speaker == "Osoba A" else "person B"
            st.session_state.draft += f"[voice: polish {sp}] \"{txt_duo}\" [pause: 0.5s] "

    st.divider()
    st.subheader("🎵 Audio")
    aud_duo = st.selectbox("Styl audio:", ["Hip-Hop", "Cinematic", "Piano", "Romantic", "Cyberpunk Synth"], label_visibility="collapsed")
    if st.button("➕ Audio"):
        st.session_state.draft += f"[audio: background {aud_duo.lower()}] "

# --- RENDER ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU DUO (DRAFT):", value=st.session_state.draft, height=120)
est = estimate_duration(st.session_state.draft)

col_a, col_b = st.columns(2)
with col_a:
    res_opt = st.selectbox("Rozdzielczość (HD):", ["720p", "480p"], index=0)
with col_b:
    dur = st.slider("Długość (s):", 5, 15, int(min(max(est, 5), 15)))

if st.button("🚀 WYPAL FINALNE WIDEO DUO (HD)", type="primary", use_container_width=True):
    # Wybór zdjęcia: priorytet ma fuzja, potem oba wgrane
    fused_img = st.session_state.active_fused_image
    
    if (fused_img or (uploaded_a and uploaded_b)) and st.session_state.draft:
        with st.spinner(f"Renderowanie Duo-Wideo 720p... To może zająć chwilę."):
            try:
                # 1. Przygotowujemy baze64 (albo fuzji, albo obu wgranych)
                if fused_img:
                    buf = io.BytesIO(); fused_img.save(buf, format="JPEG"); source_bytes = buf.getvalue()
                    b64_source = base64.b64encode(source_bytes).decode()
                    source_uri = f"data:image/jpeg;base64,{b64_source}"
                else:
                    # Jeśli nie ma fuzji, Memphis i tak przyjmie tylko jedno zdjęcie jako base_layer
                    # ale my wysyłamy fuzję jako baze do Memphis.
                    # Wyrzucamy błąd, Memphis nie obsługuje image_url jako listy, obsługuje to tylko edits.
                    raise Exception("Przed wypaleniem wideo musisz wykonać Duo-Tuning (Fuzję), aby stworzyć wspólne zdjęcie obu osób.")
                
                async def _gen_duo():
                    c = xai_sdk.AsyncClient(api_key=api_key)
                    # Memphis przyjmuje TYLKO JEDNO zdjęcie jako source_image do animacji.
                    # Dlatego my animujemy Fuzję obu osób.
                    return await c.video.generate(model="grok-imagine-video", image_url=source_uri, prompt=st.session_state.draft, duration=dur, resolution=res_opt,
                                                   timeout=timedelta(minutes=15))
                
                loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); video = loop.run_until_complete(_gen_duo())
                if video.respect_moderation:
                    st.video(requests.get(video.url).content); st.download_button("💾 POBIERZ KLIP", requests.get(video.url).content, "fuzja_v59.mp4", "video/mp4")
                else: st.error("⚠️ Wideo zablokowane przez moderację.")
            except Exception as e: st.error(f"Błąd Duo-Renderowania: {e}")
    else: st.error("⚠️ Wgraj oba zdjęcia i wykonaj Duo-Tuning (Fuzję)!")
