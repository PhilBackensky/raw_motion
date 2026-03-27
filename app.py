import streamlit as st
import xai_sdk
import asyncio
import base64
import requests
import json

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION v8.14", layout="wide", page_icon="🎬")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    pwd = st.text_input("Hasło wejścia:", type="password")
    if st.button("Wejdź"):
        if pwd == st.secrets["MY_APP_PASSWORD"]:
            st.session_state["authenticated"] = True; st.rerun()
        else: st.error("Błędne hasło."); st.stop()

# --- 2. CORE ENGINE ---
api_key = st.secrets["XAI_API_KEY"]

def elon_translator(text, context_type, subject=""):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    templates = {
        "targeted_motion": f"[motion: {subject} is ..., high-fidelity cinematic movement]",
        "scene": "[scene: ..., cinematic environment and lighting]",
        "edit": "[clothing_edit: ..., preserving original pose 1:1]"
    }
    
    template = templates.get(context_type, "[...] ")
    system_instruction = "Translate to technical English tag for Memphis engine. KEEP ALL DETAILS. Output ONLY the resulting tag."
    full_prompt = f"{system_instruction} Template: {template}. Polish Text: {text}"
    
    try:
        res = requests.post(url, headers=headers, json={
            "model": "grok-4-1-fast-non-reasoning", 
            "messages": [{"role": "user", "content": full_prompt}], 
            "temperature": 0.1
        })
        translated_tag = res.json()['choices'][0]['message']['content']
        # LOGOWANIE TŁUMACZENIA
        if "logs" not in st.session_state: st.session_state.logs = []
        st.session_state.logs.append(f"🤖 Translator: '{text}' -> {translated_tag}")
        return translated_tag
    except: return f"[{context_type}: error]"

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v8.14")
if "draft" not in st.session_state: st.session_state.draft = ""
if "logs" not in st.session_state: st.session_state.logs = []

# SIDEBAR
with st.sidebar:
    st.header("🎞️ Studio Setup")
    mode = st.radio("Tryb pracy:", ["🎬 Single Photo Video", "🎬 Interactions (Duo/Trio)", "🪄 Magic Edit"])
    st.divider()
    up_1 = st.file_uploader("Zdjęcie 1:", type=['jpg','png','jpeg'])
    up_2 = st.file_uploader("Zdjęcie 2:", type=['jpg','png','jpeg']) if "Interactions" in mode else None
    
    if st.button("✨ CZYŚĆ PROMPT"): 
        st.session_state.draft = ""; st.session_state.logs = []; st.rerun()
    if st.button("⏪ UNDO"): 
        st.session_state.draft = "\n".join(st.session_state.draft.strip().split("\n")[:-1]); st.rerun()

# PANEL REŻYSERSKI
c_img, c_tools = st.columns([1, 2])

with c_img:
    st.subheader("🖼️ Obsada")
    if up_1: st.image(up_1, use_container_width=True)
    if up_2: st.image(up_2, use_container_width=True)
    
    if st.button("👥 KROK 1: LOCK CHARACTERS", use_container_width=True):
        if "Magic Edit" in mode:
            line = "[character: <IMAGE_1> is same person. Keep original face/pose.]"
        elif "Single" in mode:
            line = "[character: <IMAGE_1> contains all subjects. Preserve identity.]"
        else:
            line = f"[character: <IMAGE_1> is person 1, <IMAGE_2> is person 2.]"
        st.session_state.draft += line + "\n"
        st.session_state.logs.append("👥 Character mapping locked.")

with c_tools:
    if "Magic Edit" in mode:
        st.subheader("🪄 Studio Przebrań")
        edit_in = st.text_area("Opisz zmianę (PL):")
        model_img = st.selectbox("Model:", ["Grok Image (Standard)", "Grok Image Pro"], index=1)
        if st.button("➕ Przygotuj Edycję"):
            st.session_state.draft += elon_translator(edit_in, "edit") + "\n"
    else:
        # WIDEO UI
        r1_c1, r1_c2, r1_c3 = st.columns(3)
        with r1_c1:
            cam_key = st.selectbox("Kamera:", ["Auto", "Full Body", "Medium Shot", "Head-to-Hip Tilt", "Steady Orbit 360", "Dolly Zoom"])
            if st.button("➕ Kamera"):
                tag = f"[camera: {cam_key}]" if cam_key != "Auto" else "[camera: AI optimization]"
                st.session_state.draft += tag + "\n"
        with r1_c2:
            txt = st.text_input("Dialog:")
            who = st.selectbox("Kto mówi:", ["1", "2"] if "Interactions" in mode else ["1"])
            if st.button("➕ Głos"):
                st.session_state.draft += f"[voice: polish person {who}] \"{txt}\" [pause: 1.0s]\n"
        with r1_c3:
            subj = st.text_input("Kto działa?", value="person 1")
            act = st.text_input("Ruch?")
            if st.button("➕ Akcja"):
                st.session_state.draft += elon_translator(act, "targeted_motion", subj) + "\n"
        
        st.divider()
        r2_c1, r2_c2, r2_c3 = st.columns(3)
        with r2_c1:
            env = st.text_input("Tło:")
            if st.button("➕ Scena"): st.session_state.draft += elon_translator(env, "scene") + "\n"
        with r2_c2:
            mus = st.selectbox("Muzyka:", ["None", "Cinematic", "Lofi", "Techno", "Jazz"])
            if st.button("➕ Muzyka"): st.session_state.draft += f"[audio: background {mus.lower()}]\n"
        with r2_c3:
            sfx = st.selectbox("SFX:", ["Laughter", "Applause", "Beach waves", "Rain"])
            if st.button("➕ SFX"): st.session_state.draft += f"[audio: {sfx.lower()}]\n"

# --- DRAFT & LOGI ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=180)

# LOGI REŻYSERA (Rozwijane)
with st.expander("📓 LOGI REŻYSERA (Debug Console)"):
    if not st.session_state.logs:
        st.write("Czekam na akcje...")
    for log in st.session_state.logs:
        st.text(log)

c_res, c_dur = st.columns(2)
with c_res: res = st.selectbox("Jakość:", ["480p", "720p"], index=1)
with c_dur: dur = st.slider("Długość klipu (s):", 1, 15, 10)

# FINAL WYPAL
if st.button("🚀 WYPAL FINALNE DZIEŁO", type="primary", use_container_width=True):
    if not up_1: st.error("Brak zdjęcia!"); st.stop()
    st.session_state.logs.append(f"🚀 Iniciacja renderu: {dur}s, {res}...")
    
    with st.spinner("Praca silników xAI..."):
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            client = xai_sdk.AsyncClient(api_key=api_key)
            refs = [f"data:image/jpeg;base64,{base64.b64encode(up_1.getvalue()).decode()}"]
            if up_2 and "Interactions" in mode:
                refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_2.getvalue()).decode()}")
            
            async def run():
                if "Magic Edit" in mode:
                    m_id = "grok-imagine-image-edit-pro" if "Pro" in model_img else "grok-imagine-image-edit"
                    return await client.image.generate(model=m_id, prompt=st.session_state.draft, image_url=refs[0])
                else:
                    return await client.video.generate(model="grok-imagine-video", prompt=st.session_state.draft, reference_image_urls=refs, duration=dur, resolution=res)

            res_data = loop.run_until_complete(run())
            if "Magic Edit" in mode: st.image(res_data.url)
            else: st.video(requests.get(res_data.url).content)
            st.session_state.logs.append("✅ Render zakończony sukcesem.")
        except Exception as e: 
            st.error(f"Błąd: {e}")
            st.session_state.logs.append(f"🔴 BŁĄD SILNIKA: {str(e)}")
