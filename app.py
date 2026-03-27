import streamlit as st
import xai_sdk
import asyncio
import base64
import requests

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION v8.11", layout="wide", page_icon="🎬")

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
        "targeted_motion": f"[motion: {subject} is ..., high-fidelity movement]",
        "scene": "[scene: ..., cinematic lighting]",
        "edit": "[clothing_edit: ..., preserving original pose 1:1]"
    }
    
    template = templates.get(context_type, "[...] ")
    system_instruction = "Translate to technical English tag for Memphis engine. DO NOT COMPRESS DETAILS. Output ONLY the resulting tag."
    full_prompt = f"{system_instruction} Template: {template}. Polish Text: {text}"
    
    try:
        res = requests.post(url, headers=headers, json={
            "model": "grok-4-1-fast-non-reasoning", 
            "messages": [{"role": "user", "content": full_prompt}], 
            "temperature": 0.1
        })
        return res.json()['choices'][0]['message']['content']
    except: return f"[{context_type}: error]"

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v8.11")
if "draft" not in st.session_state: st.session_state.draft = ""

# SIDEBAR
with st.sidebar:
    st.header("🎞️ Studio Setup")
    # Nowy tryb: Single Photo Video
    mode = st.radio("Tryb pracy:", ["🎬 Single Photo Video (Ożywianie)", "🎬 Interactions (Duo/Trio)", "🪄 Magic Edit (Static)"])
    st.divider()
    up_1 = st.file_uploader("Zdjęcie Główne (<IMAGE_1>):", type=['jpg','png','jpeg'])
    up_2 = st.file_uploader("Zdjęcie 2 (<IMAGE_2>):", type=['jpg','png','jpeg']) if "Interactions" in mode else None
    
    if st.button("✨ CZYŚĆ PROMPT"): st.session_state.draft = ""; st.rerun()
    if st.button("⏪ UNDO"): 
        st.session_state.draft = "\n".join(st.session_state.draft.strip().split("\n")[:-1]); st.rerun()

# PANEL REŻYSERSKI
c_img, c_tools = st.columns([1, 2])

with c_img:
    st.subheader("🖼️ Obsada")
    if up_1: st.image(up_1, caption="IMAGE_1", use_container_width=True)
    if up_2: st.image(up_2, caption="IMAGE_2", use_container_width=True)
    
    # KROK 1: LOCK
    if st.button("👥 KROK 1: LOCK CHARACTERS", use_container_width=True):
        if "Single" in mode:
            line = "[character: <IMAGE_1> contains all subjects. Preserve their faces and builds exactly as shown.]"
        else:
            line = f"[character: <IMAGE_1> is person 1"
            if up_2: line += ", <IMAGE_2> is person 2"
            line += ". Preserve identities 1:1.]"
        st.session_state.draft += line + "\n"

with c_tools:
    if "Video" in mode or "Interactions" in mode:
        # Rząd 1
        r1_c1, r1_c2, r1_c3 = st.columns(3)
        with r1_c1:
            st.write("🎥 **Kamera**")
            cam = st.selectbox("Ujęcie:", ["Auto (AI Director)", "steady close-up", "orbit 360", "dolly zoom", "handheld shake"])
            if st.button("➕ Kamera"):
                tag = "[camera: AI selection]" if "Auto" in cam else f"[camera: {cam}]"
                st.session_state.draft += tag + "\n"
        
        with r1_c2:
            st.write("🎙️ **Dialogi**")
            txt = st.text_input("Tekst:")
            # Dynamiczny wybór osób
            who_opt = ["Person 1", "Person 2"] if "Interactions" in mode else ["Osoba ze zdjęcia"]
            who = st.selectbox("Kto mówi:", who_opt)
            if st.button("➕ Głos"):
                p_id = "1" if "1" in who or "Osoba" in who else "2"
                st.session_state.draft += f"[voice: polish person {p_id}] \"{txt}\" [pause: 1.0s]\n"
        
        with r1_c3:
            st.write("🕺 **Akcja / Ruch**")
            # Przy jednym zdjęciu pozwalamy wpisać dowolny podmiot (np. "blondynka")
            subj_val = st.text_input("Kto działa? (np. person 1, blondynka):", value="person 1")
            act_pl = st.text_input("Co robi? (np. macha ręką):")
            if st.button("➕ Akcja"):
                st.session_state.draft += elon_translator(act_pl, "targeted_motion", subj_val) + "\n"

        st.divider()
        # Rząd 2
        r2_c1, r2_c2, r2_c3 = st.columns(3)
        with r2_c1:
            st.write("🌍 **Tło / Scena**")
            env = st.text_input("Zmień tło (PL):")
            if st.button("➕ Scena"):
                st.session_state.draft += elon_translator(env, "scene") + "\n"
        with r2_c2:
            st.write("🎵 **Muzyka**")
            bg_m = st.selectbox("Styl:", ["None", "Cinematic", "Summer Pop", "Dark Tension"])
            if st.button("➕ Muzyka"):
                st.session_state.draft += f"[audio: background {bg_m.lower()}]\n"
        with r2_c3:
            st.write("🔊 **SFX**")
            sfx = st.selectbox("Efekt:", ["Laughter", "Applause", "Beach waves", "City"])
            if st.button("➕ SFX"):
                st.session_state.draft += f"[audio: {sfx.lower()}]\n"

# RENDER
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=200)

c_res, c_dur = st.columns(2)
with c_res: res = st.selectbox("Jakość:", ["480p", "720p"], index=1)
with c_dur: dur = st.slider("Długość klipu (sekundy):", 1, 15, 10)

if st.button("🚀 WYPAL FINALNE DZIEŁO", type="primary", use_container_width=True):
    if not up_1: st.error("Wgraj zdjęcie!"); st.stop()
    with st.spinner(f"Ożywianie obrazu ({dur}s)..."):
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            client = xai_sdk.AsyncClient(api_key=api_key)
            refs = [f"data:image/jpeg;base64,{base64.b64encode(up_1.getvalue()).decode()}"]
            if up_2: refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_2.getvalue()).decode()}")
            
            async def run():
                if "Magic Edit" in mode:
                    return await client.image.generate(model="grok-imagine-image-edit", prompt=st.session_state.draft, image_url=refs[0])
                else:
                    return await client.video.generate(model="grok-imagine-video", prompt=st.session_state.draft, reference_image_urls=refs, duration=dur, resolution=res)

            res_data = loop.run_until_complete(run())
            if "Magic Edit" in mode: st.image(res_data.url)
            else: st.video(requests.get(res_data.url).content)
            st.success("🎬 Akcja!")
        except Exception as e: st.error(f"🔴 Błąd: {str(e)}")
