import streamlit as st
import xai_sdk
import asyncio
import base64
import requests

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION v8.17", layout="wide", page_icon="🎬")

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
        res = requests.post(url, headers=headers, json={"model": "grok-4-1-fast-non-reasoning", "messages": [{"role": "user", "content": full_prompt}], "temperature": 0.1})
        translated = res.json()['choices'][0]['message']['content']
        if "logs" not in st.session_state: st.session_state.logs = []
        st.session_state.logs.append(f"🤖 Translator: '{text}' -> {translated}")
        return translated
    except: return f"[{context_type}: error]"

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v8.17")
if "draft" not in st.session_state: st.session_state.draft = ""
if "logs" not in st.session_state: st.session_state.logs = []

with st.sidebar:
    st.header("🎞️ Studio Setup")
    mode = st.radio("Tryb pracy:", ["🎬 Single Photo Video", "🎬 Interactions (Duo/Trio)", "🪄 Magic Edit (Static)"])
    st.divider()
    up_1 = st.file_uploader("Zdjęcie 1:", type=['jpg','png','jpeg'])
    up_2 = st.file_uploader("Zdjęcie 2:", type=['jpg','png','jpeg']) if "Interactions" in mode else None
    if st.button("✨ CZYŚĆ PROMPT"): st.session_state.draft = ""; st.session_state.logs = []; st.rerun()
    if st.button("⏪ UNDO"): st.session_state.draft = "\n".join(st.session_state.draft.strip().split("\n")[:-1]); st.rerun()

c_img, c_tools = st.columns([1, 2])

with c_img:
    st.subheader("🖼️ Obsada")
    if up_1: st.image(up_1, use_container_width=True)
    if up_2: st.image(up_2, use_container_width=True)
    if st.button("👥 KROK 1: LOCK CHARACTERS", use_container_width=True):
        line = "[character: <IMAGE_1> same person 1:1]" if "Magic" in mode else "[character: mapping identities 1:1]"
        st.session_state.draft += line + "\n"

with c_tools:
    if "Magic Edit" in mode:
        st.subheader("🪄 Magic Edit")
        edit_desc = st.text_area("Opisz zmianę:")
        img_model = st.selectbox("Model:", ["Grok Image", "Grok Image Pro"], index=1)
        if st.button("➕ Przygotuj Edycję"): st.session_state.draft += elon_translator(edit_desc, "edit") + "\n"
    else:
        # MODULAR MULTI-SCENE SWITCH
        st.subheader("🎬 Reżyseria Wideo")
        multi_on = st.checkbox("🔥 Włącz MULTI-SCENE (Podział 7s + 8s)", value=False)
        
        # Wybór sceny do edycji
        active_scene = st.radio("Edytujesz teraz:", ["Scena 1 (0-7s)", "Scena 2 (8-15s)"]) if multi_on else "Cały Film"
        
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1:
            cam_opts = {
                "Auto": "[camera: AI selection]", "Full Body": "[camera: full body]", "Medium Shot": "[camera: medium shot]",
                "Head-to-Hip Tilt": "[camera: head to hip tilt]", "360 Orbit": "[camera: orbit 360]", "Dolly Zoom": "[camera: dolly zoom]"
            }
            cam = st.selectbox("Kamera:", list(cam_opts.keys()))
            if st.button("➕ Kamera"):
                prefix = f"[{active_scene}] " if multi_on else ""
                st.session_state.draft += f"{prefix}{cam_opts[cam]}\n"
        with r1c2:
            txt = st.text_input("Dialog:")
            if st.button("➕ Głos"):
                prefix = f"[{active_scene}] " if multi_on else ""
                st.session_state.draft += f"{prefix}[voice: polish] \"{txt}\" [pause: 1.0s]\n"
        with r1c3:
            subj = st.text_input("Kto?", value="person 1")
            act = st.text_input("Akcja (PL):")
            if st.button("➕ Akcja"):
                prefix = f"[{active_scene}] " if multi_on else ""
                st.session_state.draft += f"{prefix}{elon_translator(act, 'targeted_motion', subj)}\n"

        st.divider()
        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            env = st.text_input("Scena:")
            if st.button("➕ Scena"): st.session_state.draft += elon_translator(env, "scene") + "\n"
        with r2c2:
            mus = st.selectbox("Muzyka:", ["None", "Cinematic", "Lofi", "Techno", "Jazz"])
            if st.button("➕ Muzyka"): st.session_state.draft += f"[audio: background {mus.lower()}]\n"
        with r2c3:
            sfx = st.selectbox("SFX:", ["Laughter", "Beach waves", "Rain", "Forest"])
            if st.button("➕ SFX"): st.session_state.draft += f"[audio: {sfx.lower()}]\n"
        
        if multi_on and st.button("✂️ DODAJ CIĘCIE (CUT)"):
            st.session_state.draft += "[cut: transition between scene 1 and 2]\n"

st.divider()
st.session_state.draft = st.text_area("🛠️ DRAFT:", value=st.session_state.draft, height=180)
with st.expander("📓 LOGI REŻYSERA"):
    for log in st.session_state.logs: st.text(log)

if "Magic Edit" not in mode:
    c_res, c_dur = st.columns(2)
    with c_res: res = st.selectbox("Jakość:", ["480p", "720p"], index=1)
    with c_dur: dur = st.slider("Długość (s):", 1, 15, 15 if multi_on else 10)
else:
    res, dur = "720p", 1 

if st.button("🚀 WYPAL FINALNE DZIEŁO", type="primary", use_container_width=True):
    if not up_1: st.error("Brak obrazu!"); st.stop()
    with st.spinner("Mielenie danych..."):
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            client = xai_sdk.AsyncClient(api_key=api_key)
            refs = [f"data:image/jpeg;base64,{base64.b64encode(up_1.getvalue()).decode()}"]
            if up_2 and "Interactions" in mode: refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_2.getvalue()).decode()}")
            async def run():
                if "Magic Edit" in mode:
                    m_id = "grok-imagine-image-edit-pro" if "Pro" in img_model else "grok-imagine-image-edit"
                    return await client.image.generate(model=m_id, prompt=st.session_state.draft, image_url=refs[0])
                else:
                    return await client.video.generate(model="grok-imagine-video", prompt=st.session_state.draft, reference_image_urls=refs, duration=dur, resolution=res)
            res_data = loop.run_until_complete(run())
            if "Magic Edit" in mode: st.image(res_data.url)
            else: st.video(requests.get(res_data.url).content)
        except Exception as e: st.error(f"Błąd: {e}")
