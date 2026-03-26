import streamlit as st
import xai_sdk
import asyncio
import base64
import requests
from datetime import timedelta

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION v8.5", layout="wide", page_icon="🎬")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    pwd = st.text_input("Hasło wejścia:", type="password")
    if st.button("Wejdź"):
        if pwd == st.secrets["MY_APP_PASSWORD"]:
            st.session_state["authenticated"] = True; st.rerun()
        else: st.error("Błędne hasło."); st.stop()

# --- 2. ELON TRANSLATOR CORE ---
api_key = st.secrets["XAI_API_KEY"]

def elon_translator(text, context_type):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # Mapowanie kontekstu na tagi techniczne
    tag_templates = {
        "motion": "[motion: ..., high-fidelity facial interaction]",
        "edit": "[clothing_edit: ..., preserving pose 1:1]",
        "scene": "[scene: ..., cinematic lighting]",
        "auto_cam": "[camera: generate best cinematic angle for: ...]"
    }
    
    template = tag_templates.get(context_type, "[...] ")
    prompt = f"Translate the following Polish description into a technical tag for the Memphis engine using this format: {template}. Output ONLY the resulting tag. Text: {text}"
    
    try:
        res = requests.post(url, headers=headers, json={
            "model": "grok-4-1-fast-non-reasoning", 
            "messages": [{"role": "user", "content": prompt}], 
            "temperature": 0.1
        })
        return res.json()['choices'][0]['message']['content']
    except: return f"[{context_type}: translation error]"

# --- 3. INTERFACE & DRAFT BUILDING ---
st.title("🎥 RAWMOTION Director v8.5")
if "draft" not in st.session_state: st.session_state.draft = ""

# SIDEBAR: SETUP
with st.sidebar:
    st.header("🎞️ Studio Mode")
    mode = st.radio("Tryb:", ["🎬 Interactions (Duo/Trio)", "🪄 Magic Edit (1 Foto)"])
    st.divider()
    up_1 = st.file_uploader("Postać 1 (<IMAGE_1>):", type=['jpg','png','jpeg'])
    up_2 = st.file_uploader("Postać 2 (<IMAGE_2>):", type=['jpg','png','jpeg']) if "Interactions" in mode else None
    
    if st.button("✨ CZYŚĆ SCENARIUSZ"): st.session_state.draft = ""; st.rerun()
    if st.button("⏪ COFNIJ"): 
        st.session_state.draft = "\n".join(st.session_state.draft.strip().split("\n")[:-1])
        st.rerun()

# PANEL KONTROLNY 3x2
c_img, c_tools = st.columns([1, 2])

with c_img:
    st.subheader("🖼️ Obsada")
    if up_1: st.image(up_1, caption="IMAGE_1", use_container_width=True)
    if up_2: st.image(up_2, caption="IMAGE_2", use_container_width=True)
    
    # 1. CHARACTER LOCK (KROK 1)
    if st.button("👥 KROK 1: Wprowadź Postacie", use_container_width=True):
        line = f"[character: <IMAGE_1> is person 1 on the left"
        if up_2: line += ", <IMAGE_2> is person 2 on the right"
        line += ". Both preserve faces and build from references.]"
        st.session_state.draft += line + "\n"

with c_tools:
    if "Interactions" in mode:
        r1_c1, r1_c2, r1_c3 = st.columns(3)
        with r1_c1:
            st.write("🎥 **Kamera**")
            cam_opt = st.selectbox("Ujęcie:", ["Auto (AI Vision)", "orbit 360", "steady close-up", "handheld shake", "dolly zoom"])
            if st.button("➕ Dodaj Kamerę"):
                if "Auto" in cam_opt:
                    st.session_state.draft += "[camera: AI selection for best dynamic interaction]\n"
                else:
                    st.session_state.draft += f"[camera: {cam_opt}]\n"
        
        with r1_c2:
            st.write("🎙️ **Dialog**")
            txt = st.text_input("Kwestia:")
            who = st.selectbox("Mówi:", ["Osoba 1 (Lewa)", "Osoba 2 (Prawa)"])
            if st.button("➕ Dodaj Głos"):
                p_id = who.split()[1]
                p_pos = "left" if p_id == "1" else "right"
                st.session_state.draft += f"[voice: polish person {p_id} on the {p_pos}] \"{txt}\" [pause: 1.0s]\n"
        
        with r1_c3:
            st.write("🕺 **Interakcja / Ruch**")
            move = st.text_input("Opisz akcję (PL):", placeholder="np. rozmawiają na ławce")
            if st.button("➕ Tłumacz Akcję"):
                st.session_state.draft += elon_translator(move, "motion") + "\n"

        st.divider()
        r2_c4, r2_c5, r2_c6 = st.columns(3)
        with r2_c4:
            st.write("🎵 **Atmosfera**")
            env = st.text_input("Tło/Scena (PL):", placeholder="np. park o zachodzie")
            if st.button("➕ Ustaw Scenę"):
                st.session_state.draft += elon_translator(env, "scene") + "\n"
        with r2_c5:
            st.write("🔊 **SFX**")
            sfx = st.selectbox("Efekt:", ["Laughter", "Birds chirping", "City noise", "Applause"])
            if st.button("➕ SFX"): st.session_state.draft += f"[audio: {sfx.lower()}]\n"
        with r2_c6:
            st.write("🏃 **Zakończenie**")
            end = st.text_input("Koniec (PL):", placeholder="np. wstają i odchodzą")
            if st.button("➕ Dodaj Wyjście"):
                st.session_state.draft += elon_translator(end, "motion") + "\n"

    else: # MAGIC EDIT
        edit_desc = st.text_area("Opisz zmianę ubioru (PL):", placeholder="np. obcisły strój reprezentacji polski")
        if st.button("🪄 Przygotuj Edycję Zdjęcia"):
            st.session_state.draft = f"[character: <IMAGE_1> is same person] " + elon_translator(edit_desc, "edit")

# --- RENDER ENGINE ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=200)

if st.button("🚀 WYPAL FINALNE DZIEŁO", type="primary", use_container_width=True):
    if not up_1: st.error("Brak zdjęcia!"); st.stop()
    with st.spinner("Silnik Memphis pracuje nad Twoim scenariuszem..."):
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            client = xai_sdk.AsyncClient(api_key=api_key)
            
            refs = [f"data:image/jpeg;base64,{base64.b64encode(up_1.getvalue()).decode()}"]
            if up_2: refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_2.getvalue()).decode()}")
            
            async def process():
                if "Magic Edit" in mode:
                    return await client.image.generate(model="grok-imagine-image-edit", prompt=st.session_state.draft, image_url=refs[0])
                else:
                    return await client.video.generate(model="grok-imagine-video", prompt=st.session_state.draft, reference_image_urls=refs, duration=10, resolution="720p")

            res = loop.run_until_complete(process())
            if "Magic Edit" in mode: st.image(res.url)
            else: st.video(requests.get(res.url).content)
            st.success("🎬 Akcja! Gotowe.")
        except Exception as e: st.error(f"🔴 Błąd Silnika: {str(e)}")
