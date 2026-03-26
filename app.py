import streamlit as st
import xai_sdk
import asyncio
import base64
import requests
from datetime import timedelta

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION v8.4", layout="wide", page_icon="🎬")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    pwd = st.text_input("Hasło wejścia:", type="password")
    if st.button("Wejdź"):
        if pwd == st.secrets["MY_APP_PASSWORD"]:
            st.session_state["authenticated"] = True; st.rerun()
        else: st.error("Błędne hasło."); st.stop()

# --- 2. CORE ENGINE LOGIC (BEBECHY) ---
api_key = st.secrets["XAI_API_KEY"]

def elon_translator(text, context_type):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    tag_map = {"motion": "[motion: ...]", "edit": "[clothing_edit: ...]"}
    tag = tag_map.get(context_type, "[...] ")
    prompt = f"Translate to technical tag for Memphis engine using {tag}. Output ONLY tag. Text: {text}"
    try:
        res = requests.post(url, headers=headers, json={"model": "grok-4-1-fast-non-reasoning", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2})
        return res.json()['choices'][0]['message']['content']
    except: return f"[{context_type}: error]"

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v8.4")
if "draft" not in st.session_state: st.session_state.draft = ""

# --- SIDEBAR: TRYBY PRACY ---
with st.sidebar:
    st.header("🎞️ Wybór Studia")
    studio_mode = st.radio("Tryb pracy:", ["🎬 Video Interactions (Duo/Trio)", "🪄 Magic Edit (Przebieranki - 1 Foto)"])
    
    st.divider()
    up_1 = st.file_uploader("Zdjęcie 1 (<IMAGE_1>):", type=['jpg','png','jpeg'])
    up_2 = st.file_uploader("Zdjęcie 2 (<IMAGE_2>):", type=['jpg','png','jpeg']) if "Video" in studio_mode else None
    up_3 = st.file_uploader("Zdjęcie 3 (<IMAGE_3>):", type=['jpg','png','jpeg']) if "Video" in studio_mode else None

    if st.button("✨ Resetuj Scenariusz"): st.session_state.draft = ""; st.rerun()

# --- PANEL KONTROLNY ---
col_preview, col_tools = st.columns([1, 2])

with col_preview:
    st.subheader("🖼️ Podgląd Referencji")
    if up_1: st.image(up_1, caption="IMAGE_1 (Główna)", use_container_width=True)
    if up_2: st.image(up_2, caption="IMAGE_2", use_container_width=True)

with col_tools:
    if "Video" in studio_mode:
        # 6 MINIMENU (2x3)
        row1 = st.container()
        c1, c2, c3 = row1.columns(3)
        with c1:
            st.write("🎥 **Kamera**")
            cam_dict = {
                "steady close-up": "Zbliżenie (nieruchome)",
                "orbit 360": "Obrót dookoła (360)",
                "handheld shake": "Z ręki (realistyczne)",
                "whip pan": "Szybka panorama",
                "dolly zoom": "Najazd (Hitchcock)",
                "low angle hero": "Z dołu (heroizm)",
                "drone sweep": "Z lotu ptaka",
                "pov shot": "Z oczu postaci"
            }
            cam_key = st.selectbox("Ujęcie:", list(cam_dict.keys()), format_func=lambda x: f"{x} ({cam_dict[x]})")
            if st.button("➕ Kamera"): st.session_state.draft += f"[camera: {cam_key}] "
            
        with c2:
            st.write("🎙️ **Dialog**")
            txt = st.text_input("Kwestia:")
            who = st.selectbox("Kto mówi:", ["Osoba 1 (Lewa)", "Osoba 2 (Prawa)", "Osoba 3"])
            if st.button("➕ Dialog"):
                tag = who.split()[1]
                pos = "left" if tag == "1" else "right"
                st.session_state.draft += f"[voice: polish person {tag} on the {pos}] \"{txt}\" [pause: 1.0s] "
                
        with c3:
            st.write("🕺 **Interakcja**")
            act_pl = st.text_input("Co robią? (PL):")
            if st.button("➕ Tłumacz Ruch"):
                st.session_state.draft += f"{elon_translator(act_pl, 'motion')} "

        st.write("---")
        row2 = st.container()
        c4, c5, c6 = row2.columns(3)
        with c4:
            st.write("🎵 **Muzyka**")
            mus = st.selectbox("Styl:", ["Cinematic Tension", "Summer Pop", "Dark Techno", "Romantic Piano", "Epic Orchestral"])
            if st.button("➕ Audio"): st.session_state.draft += f"[audio: background {mus.lower()}] "
        with c5:
            st.write("🔊 **SFX**")
            sfx = st.selectbox("Efekt:", ["Applause", "Laughter", "Street Noise", "Thunder", "Crowd Cheering", "Heartbeat"])
            if st.button("➕ SFX"): st.session_state.draft += f"[audio: {sfx.lower()}] "
        with c6:
            st.write("🎭 **Filtry Audio**")
            fil = st.selectbox("Efekt:", ["None", "Whisper", "Radio voice", "Echo", "Large Hall", "Underwater"])
            if st.button("➕ Filtr"): st.session_state.draft += f"[audio: filter {fil.lower()}] "

    else: # TRYB MAGIC EDIT
        st.subheader("🪄 Studio Przebrań (In-Painting)")
        edit_pl = st.text_area("Opisz zmianę stroju (np. 'ubierz ją w obcisły strój reprezentacji polski'):")
        if st.button("➕ Przygotuj Edycję"):
            st.session_state.draft = f"[character: <IMAGE_1> is the same person. Preserve pose/face 1:1.] {elon_translator(edit_pl, 'edit')}"

# --- FINALIZACJA ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=120)

if st.button("🚀 WYPAL FINALNE DZIEŁO", type="primary", use_container_width=True):
    if not up_1: st.error("Wgraj zdjęcie!"); st.stop()
    with st.spinner("Praca silnika... Proszę czekać."):
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            client = xai_sdk.AsyncClient(api_key=api_key)
            
            # Serce Silnika: Kodowanie i prefixing
            refs = [f"data:image/jpeg;base64,{base64.b64encode(up_1.getvalue()).decode()}"]
            if up_2: refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_2.getvalue()).decode()}")
            if up_3: refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_3.getvalue()).decode()}")
            
            prefix = "[character: <IMAGE_1> is person 1" + (" on the left" if up_2 else "")
            if up_2: prefix += ", <IMAGE_2> is person 2 on the right"
            prefix += "]. "
            
            final_p = prefix + st.session_state.draft
            
            async def run():
                if "Magic Edit" in studio_mode:
                    # Wywołanie dla obrazu
                    return await client.image.generate(model="grok-imagine-image-edit", prompt=final_p, image_url=refs[0])
                else:
                    # Wywołanie dla wideo
                    return await client.video.generate(model="grok-imagine-video", prompt=final_p, reference_image_urls=refs, duration=10, resolution="720p")

            res = loop.run_until_complete(run())
            st.video(requests.get(res.url).content) if "Video" in studio_mode else st.image(res.url)
            st.success("✅ Gotowe!")
        except Exception as e: st.error(f"🔴 Błąd: {str(e)}")
