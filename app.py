import streamlit as st
import xai_sdk
import asyncio
import base64
import requests

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION v8.16", layout="wide", page_icon="🎬")

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
        "scene": "[scene: ..., cinematic environmental lighting]",
        "edit": "[clothing_edit: ..., preserving original pose and face 1:1]"
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
        translated = res.json()['choices'][0]['message']['content']
        if "logs" not in st.session_state: st.session_state.logs = []
        st.session_state.logs.append(f"🤖 Translator: '{text}' -> {translated}")
        return translated
    except: return f"[{context_type}: error]"

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v8.16")
if "draft" not in st.session_state: st.session_state.draft = ""
if "logs" not in st.session_state: st.session_state.logs = []

# SIDEBAR
with st.sidebar:
    st.header("🎞️ Studio Setup")
    mode = st.radio("Tryb pracy:", ["🎬 Single Photo Video", "🎬 Interactions (Duo/Trio)", "🪄 Magic Edit (Static)"])
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
            line = "[character: <IMAGE_1> is same person. Keep original face/pose 1:1.]"
        elif "Single" in mode:
            line = "[character: <IMAGE_1> holds all subjects. Preserve identity.]"
        else:
            line = f"[character: <IMAGE_1> is person 1, <IMAGE_2> is person 2.]"
        st.session_state.draft += line + "\n"
        st.session_state.logs.append("👥 Identity Locked.")

with c_tools:
    if "Magic Edit" in mode:
        st.subheader("🪄 Magic Edit (Zdjęcie)")
        edit_desc = st.text_area("Opisz zmianę (np. skąpe bikini):")
        img_model = st.selectbox("Wybierz model:", ["Grok Image", "Grok Image Pro"], index=1)
        if st.button("➕ Przygotuj Edycję"):
            st.session_state.draft += elon_translator(edit_desc, "edit") + "\n"
    else:
        # ROZBUDOWANE WIDEO (v8.12 + PL Opisy)
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1:
            cam_opts = {
                "Auto (AI Director)": "[camera: AI selection]",
                "Full Body Shot (Cała sylwetka)": "[camera: full body long shot]",
                "Medium Shot (Połowa sylwetki)": "[camera: medium shot waist up]",
                "Head-to-Hip Tilt (Od głowy do bioder)": "[camera: slow tilt from head to hips]",
                "Extreme Close-up (Zbliżenie na twarz)": "[camera: extreme close-up]",
                "Steady Orbit 360 (Obrót dookoła)": "[camera: 360 orbit]",
                "Dolly Zoom (Efekt Vertigo)": "[camera: dolly zoom]",
                "Handheld Shaky (Z ręki)": "[camera: shaky handheld cam]",
                "Dutch Angle (Pochylona kamera)": "[camera: cinematic dutch angle tilt]",
                "Low Angle (Ujęcie z dołu)": "[camera: low angle hero shot]"
            }
            cam_key = st.selectbox("Kamera:", list(cam_opts.keys()))
            if st.button("➕ Kamera"): st.session_state.draft += cam_opts[cam_key] + "\n"
        with r1c2:
            txt = st.text_input("Dialog:")
            who = st.selectbox("Mówi:", ["1", "2"] if "Interactions" in mode else ["1"])
            if st.button("➕ Głos"): st.session_state.draft += f"[voice: polish person {who}] \"{txt}\" [pause: 1.0s]\n"
        with r1c3:
            subj = st.text_input("Kto działa?", value="person 1")
            act = st.text_input("Akcja (PL):")
            if st.button("➕ Akcja"): st.session_state.draft += elon_translator(act, "targeted_motion", subj) + "\n"
        
        st.divider()
        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            env = st.text_input("Scena:")
            if st.button("➕ Scena"): st.session_state.draft += elon_translator(env, "scene") + "\n"
        with r2c2:
            mus = st.selectbox("Muzyka:", [
                "None", "Cinematic Orchestral", "Summer Lofi HipHop", "Romantic Piano", 
                "Cyberpunk Techno", "Dark Jazz Noir", "Heavy Metal Energy", "Elevator Chill"
            ])
            if st.button("➕ Muzyka"): st.session_state.draft += f"[audio: background {mus.lower()}]\n"
        with r2c3:
            sfx = st.selectbox("SFX:", [
                "Laughter", "Beach waves", "Rain & Thunder", "Forest Birds", 
                "Street Traffic", "Crowd Applause", "Footsteps on wood", "Coffee shop ambiance"
            ])
            if st.button("➕ SFX"): st.session_state.draft += f"[audio: {sfx.lower()}]\n"

# --- RENDER & LOGS ---
st.divider()
st.session_state.draft = st.text_area("🛠️ OŚ CZASU (DRAFT):", value=st.session_state.draft, height=180)

with st.expander("📓 LOGI REŻYSERA (Director's Log)"):
    if not st.session_state.logs: st.write("Czekam na akcje...")
    for log in st.session_state.logs: st.text(log)

if "Magic Edit" not in mode:
    c_res, c_dur = st.columns(2)
    with c_res: res = st.selectbox("Jakość:", ["480p", "720p"], index=1)
    with c_dur: dur = st.slider("Długość klipu (s):", 1, 15, 10)
else:
    res, dur = "720p", 1 

if st.button("🚀 WYPAL FINALNE DZIEŁO", type="primary", use_container_width=True):
    if not up_1: st.error("Brak obrazu!"); st.stop()
    st.session_state.logs.append(f"🚀 Render start: {mode}")
    with st.spinner("Praca silników xAI..."):
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            client = xai_sdk.AsyncClient(api_key=api_key)
            refs = [f"data:image/jpeg;base64,{base64.b64encode(up_1.getvalue()).decode()}"]
            if up_2 and "Interactions" in mode:
                refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_2.getvalue()).decode()}")
            
            async def run():
                if "Magic Edit" in mode:
                    m_id = "grok-imagine-image-edit-pro" if "Pro" in img_model else "grok-imagine-image-edit"
                    return await client.image.generate(model=m_id, prompt=st.session_state.draft, image_url=refs[0])
                else:
                    return await client.video.generate(model="grok-imagine-video", prompt=st.session_state.draft, reference_image_urls=refs, duration=dur, resolution=res)

            res_data = loop.run_until_complete(run())
            if "Magic Edit" in mode: st.image(res_data.url, caption="✅ Zedytowane Zdjęcie")
            else: st.video(requests.get(res_data.url).content)
            st.session_state.logs.append("✅ Render OK.")
        except Exception as e: st.error(f"Błąd: {e}"); st.session_state.logs.append(f"🔴 BŁĄD: {e}")
