import streamlit as st
import xai_sdk
import asyncio
import base64
import requests

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION v8.12", layout="wide", page_icon="🎬")

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
        return res.json()['choices'][0]['message']['content']
    except: return f"[{context_type}: error]"

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v8.12")
if "draft" not in st.session_state: st.session_state.draft = ""

# SIDEBAR
with st.sidebar:
    st.header("🎞️ Studio Setup")
    mode = st.radio("Tryb pracy:", ["🎬 Single Photo Video", "🎬 Interactions (Duo/Trio)", "🪄 Magic Edit"])
    st.divider()
    up_1 = st.file_uploader("Zdjęcie 1 (<IMAGE_1>):", type=['jpg','png','jpeg'])
    up_2 = st.file_uploader("Zdjęcie 2 (<IMAGE_2>):", type=['jpg','png','jpeg']) if "Interactions" in mode else None
    
    if st.button("✨ CZYŚĆ PROMPT"): st.session_state.draft = ""; st.rerun()
    if st.button("⏪ COFNIJ (UNDO)"): 
        st.session_state.draft = "\n".join(st.session_state.draft.strip().split("\n")[:-1]); st.rerun()

# PANEL REŻYSERSKI
c_img, c_tools = st.columns([1, 2])

with c_img:
    st.subheader("🖼️ Obsada")
    if up_1: st.image(up_1, caption="IMAGE_1", use_container_width=True)
    if up_2: st.image(up_2, caption="IMAGE_2", use_container_width=True)
    
    if st.button("👥 KROK 1: LOCK CHARACTERS", use_container_width=True):
        if "Single" in mode:
            line = "[character: <IMAGE_1> holds all subjects. Preserve faces/builds 1:1.]"
        else:
            line = f"[character: <IMAGE_1> is person 1, <IMAGE_2> is person 2. Preserve identities.]"
        st.session_state.draft += line + "\n"

with c_tools:
    if "Video" in mode or "Interactions" in mode:
        # Rząd 1: Kamera, Dialogi, Akcja
        r1_c1, r1_c2, r1_c3 = st.columns(3)
        with r1_c1:
            st.write("🎥 **Kamera (Optics)**")
            cam_options = {
                "Auto (AI Director)": "[camera: AI selection]",
                "Full Body Shot": "[camera: full body long shot]",
                "Medium Shot (Half Body)": "[camera: medium shot waist up]",
                "Head-to-Hip Tilt": "[camera: slow tilt from head to hips]",
                "Extreme Close-up": "[camera: extreme close-up on face]",
                "Steady Orbit 360": "[camera: 360-degree steady orbit]",
                "Dolly Zoom (Vertigo)": "[camera: dolly zoom effect]",
                "Handheld Shaky Cam": "[camera: shaky handheld camera]",
                "Dutch Angle (Tilted)": "[camera: cinematic dutch angle tilt]",
                "Low Angle (Hero)": "[camera: low angle looking up]"
            }
            cam_key = st.selectbox("Ujęcie:", list(cam_options.keys()))
            if st.button("➕ Kamera"):
                st.session_state.draft += cam_options[cam_key] + "\n"
        
        with r1_c2:
            st.write("🎙️ **Głos (Dialog)**")
            txt = st.text_input("Kwestia:")
            who_v = ["Person 1", "Person 2"] if "Interactions" in mode else ["Osoba ze zdjęcia"]
            who = st.selectbox("Mówi:", who_v)
            if st.button("➕ Głos"):
                p_id = "1" if "1" in who or "Osoba" in who else "2"
                st.session_state.draft += f"[voice: polish person {p_id}] \"{txt}\" [pause: 1.0s]\n"
        
        with r1_c3:
            st.write("🕺 **Ruch (Motion)**")
            subj_val = st.text_input("Kto działa?", value="person 1")
            act_pl = st.text_input("Co robi?")
            if st.button("➕ Akcja"):
                st.session_state.draft += elon_translator(act_pl, "targeted_motion", subj_val) + "\n"

        st.divider()
        # Rząd 2: Scena, Muzyka, SFX
        r2_c1, r2_c2, r2_c3 = st.columns(3)
        with r2_c1:
            st.write("🌍 **Tło / Scena**")
            env = st.text_input("Lokalizacja:")
            if st.button("➕ Scena"):
                st.session_state.draft += elon_translator(env, "scene") + "\n"
        with r2_c2:
            st.write("🎵 **Muzyka (BG)**")
            bg_music = st.selectbox("Gatunek:", [
                "None", "Cinematic Orchestral", "Summer Lofi HipHop", "Romantic Piano", 
                "Cyberpunk Techno", "Dark Jazz Noir", "Heavy Metal Energy", "Elevator Chill"
            ])
            if st.button("➕ Muzyka"):
                st.session_state.draft += f"[audio: background {bg_music.lower()}]\n"
        with r2_c3:
            st.write("🔊 **SFX (Foley)**")
            sfx = st.selectbox("Efekt:", [
                "Laughter", "Beach waves", "Rain & Thunder", "Forest Birds", 
                "Street Traffic", "Crowd Applause", "Footsteps on wood", "Coffee shop ambiance"
            ])
            if st.button("➕ SFX"):
                st.session_state.draft += f"[audio: {sfx.lower()}]\n"

    else: # MAGIC EDIT
        edit_desc = st.text_area("Opisz zmianę stroju lub wyglądu:")
        if st.button("🪄 Edytuj Zdjęcie"):
            st.session_state.draft = f"[character: <IMAGE_1> same person] " + elon_translator(edit_desc, "edit")

# RENDER ENGINE
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=200)

c_res, c_dur = st.columns(2)
with c_res: res = st.selectbox("Jakość:", ["480p", "720p"], index=1)
with c_dur: dur = st.slider("Długość klipu (sekundy):", 1, 15, 10)

if st.button("🚀 WYPAL FINALNE DZIEŁO", type="primary", use_container_width=True):
    if not up_1: st.error("Wgraj zdjęcie główne!"); st.stop()
    with st.spinner(f"Produkcja w toku ({dur}s)..."):
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            client = xai_sdk.AsyncClient(api_key=api_key)
            refs = [f"data:image/jpeg;base64,{base64.b64encode(up_1.getvalue()).decode()}"]
            if up_2 and "Interactions" in mode:
                refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_2.getvalue()).decode()}")
            
            async def run():
                if "Magic Edit" in mode:
                    return await client.image.generate(model="grok-imagine-image-edit", prompt=st.session_state.draft, image_url=refs[0])
                else:
                    return await client.video.generate(model="grok-imagine-video", prompt=st.session_state.draft, reference_image_urls=refs, duration=dur, resolution=res)

            res_data = loop.run_until_complete(run())
            if "Magic Edit" in mode: st.image(res_data.url)
            else: st.video(requests.get(res_data.url).content)
            st.success("🎬 Produkcja zakończona pomyślnie!")
        except Exception as e: st.error(f"🔴 Błąd silnika: {str(e)}")
