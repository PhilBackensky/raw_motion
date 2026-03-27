import streamlit as st
import xai_sdk
import asyncio
import base64
import requests

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION v8.13", layout="wide", page_icon="🎬")

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

def elon_translator(text, context_type, subject=""):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # Precyzyjna instrukcja dla edycji: zakaz zmian pozy/twarzy
    if context_type == "edit":
        template = "[clothing_edit: ..., preserving original pose and face 1:1]"
        system_instruction = "Translate Polish clothing description to technical English. Output ONLY the resulting tag."
    else:
        templates = {
            "targeted_motion": f"[motion: {subject} is ..., high-fidelity cinematic movement]",
            "scene": "[scene: ..., cinematic environmental lighting]"
        }
        template = templates.get(context_type, "[...] ")
        system_instruction = "Translate to technical English tag for Memphis engine. Output ONLY resulting tag."
    
    full_prompt = f"{system_instruction} Template: {template}. Polish Text: {text}"
    
    try:
        res = requests.post(url, headers=headers, json={
            "model": "grok-4-1-fast-non-reasoning", 
            "messages": [{"role": "user", "content": full_prompt}], 
            "temperature": 0.1
        })
        return res.json()['choices'][0]['message']['content']
    except: return f"[{context_type}: translation error]"

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v8.13")
if "draft" not in st.session_state: st.session_state.draft = ""

# SIDEBAR: SETUP
with st.sidebar:
    st.header("🎞️ Studio Setup")
    mode = st.radio("Tryb pracy:", ["🎬 Single Photo Video", "🎬 Interactions (Duo/Trio)", "🪄 Magic Edit (Static)"])
    st.divider()
    up_1 = st.file_uploader("Zdjęcie Główne (<IMAGE_1>):", type=['jpg','png','jpeg'])
    up_2 = st.file_uploader("Zdjęcie 2 (<IMAGE_2>):", type=['jpg','png','jpeg']) if "Interactions" in mode else None
    
    if st.button("✨ CZYŚĆ PROMPT"): st.session_state.draft = ""; st.rerun()
    if st.button("⏪ UNDO"): 
        st.session_state.draft = "\n".join(st.session_state.draft.strip().split("\n")[:-1]); st.rerun()

# PANEL KONTROLNY 
c_preview, c_tools = st.columns([1, 2])

with c_preview:
    st.subheader("🖼️ Obsada")
    if up_1: st.image(up_1, caption="IMAGE_1", use_container_width=True)
    if up_2: st.image(up_2, caption="IMAGE_2", use_container_width=True)
    
    # KROK 1: LOCK
    if st.button("👥 KROK 1: LOCK CHARACTERS", use_container_width=True):
        if "Magic Edit" in mode:
            line = "[character: <IMAGE_1> is same person. Keep original face and pose exactly.]"
        elif "Single" in mode:
            line = "[character: <IMAGE_1> contains all subjects. Preserve identity 1:1.]"
        else:
            line = f"[character: <IMAGE_1> is person 1, <IMAGE_2> is person 2. Preserve identities.]"
        st.session_state.draft += line + "\n"

with c_tools:
    if "Magic Edit" in mode:
        st.subheader("🪄 Studio Przebrań (Static)")
        edit_input = st.text_area("Opisz zmianę ubioru lub wyglądu (np. obcisły strój reprezentacji polski):")
        if st.button("➕ Przygotuj Edycję Zdjęcia"):
            st.session_state.draft += elon_translator(edit_input, "edit") + "\n"
        
        # Wybór modelu tylko dla Magic Edit
        st.write("---")
        img_model_choice = st.selectbox("Wybierz model:", ["Grok Image (Standard)", "Grok Image Pro"], index=1)
        # Ustawiamy dedykowaną nazwę modelu xAI
        img_model_id = "grok-imagine-image-edit-pro" if "Pro" in img_model_choice else "grok-imagine-image-edit"

    else: # TRYBY WIDEO
        # (Logika wideo v8.12 zostaje tutaj, skrócona dla przejrzystości kodu)
        r1 = st.container(); c1,c2,c3 = r1.columns(3)
        with c1: st.write("🎥 Kamera"); cam = st.selectbox("Ujęcie:", ["orbit 360", "steady close-up"])
        with c2: st.write("🎙️ Dialog"); txt = st.text_input("Tekst:"); who = st.selectbox("Kto mówi:", ["1", "2"])
        with c3: st.write("🕺 Akcja"); subj=st.text_input("Kto?", "1"); act=st.text_input("Ruch?")
        
        if st.button("➕ Dodaj do Osi Czasu"):
            if txt: st.session_state.draft += f"[voice: polish person {who}] \"{txt}\" [pause: 1.0s]\n"
            if act: st.session_state.draft += elon_translator(act, "targeted_motion", subj) + "\n"
            if cam: st.session_state.draft += f"[camera: {cam}]\n"

# --- RENDER ENGINE & FINALIZACJA ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=180)

# Ukrywamy suwaki wideo w trybie Magic Edit
if "Magic Edit" not in mode:
    c_res, c_dur = st.columns(2)
    with c_res: res = st.selectbox("Jakość:", ["480p", "720p"], index=1)
    with c_dur: dur = st.slider("Długość klipu (sekundy):", 1, 15, 10)
else:
    # Definiujemy domyślne dla edycji zdjęcia, żeby kod się nie wysypał, ale ich nie pokazujemy
    res, dur = "720p", 1

if st.button("🚀 WYPAL FINALNE DZIEŁO", type="primary", use_container_width=True):
    if not up_1: st.error("Wgraj zdjęcie główne!"); st.stop()
    
    # Wybieramy nazwę akcji w spinnerze
    act_name = "Edycja zdjęcia..." if "Magic Edit" in mode else f"Render wideo ({dur}s)..."
    
    with st.spinner(act_name):
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            client = xai_sdk.AsyncClient(api_key=api_key)
            refs = [f"data:image/jpeg;base64,{base64.b64encode(up_1.getvalue()).decode()}"]
            if up_2 and "Interactions" in mode:
                refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_2.getvalue()).decode()}")
            
            async def run():
                if "Magic Edit" in mode:
                    # Wywołanie dla STATYCZNEGO zdjęcia (v8.13 Fix)
                    return await client.image.generate(model=img_model_id, prompt=st.session_state.draft, image_url=refs[0])
                else:
                    # Wywołanie dla wideo (Memphis)
                    return await client.video.generate(model="grok-imagine-video", prompt=st.session_state.draft, reference_image_urls=refs, duration=dur, resolution=res)

            res_data = loop.run_until_complete(run())
            # Wyświetlamy zdjęcie LUB wideo
            if "Magic Edit" in mode: st.image(res_data.url, caption="✅ Zedytowane Zdjęcie")
            else: st.video(requests.get(res_data.url).content)
            st.success("✅ Gotowe!")
        except Exception as e: st.error(f"🔴 Błąd: {str(e)}")
