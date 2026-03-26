import streamlit as st
import xai_sdk
import asyncio
import base64
import requests
from datetime import timedelta

# --- 1. CONFIG & SECURITY ---
st.set_page_config(page_title="RAWMOTION v8.9", layout="wide", page_icon="🎬")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    pwd = st.text_input("Hasło wejścia:", type="password")
    if st.button("Wejdź"):
        if pwd == st.secrets["MY_APP_PASSWORD"]:
            st.session_state["authenticated"] = True; st.rerun()
        else: st.error("Błędne hasło."); st.stop()

# --- 2. CORE ENGINE & TRANSLATOR ---
api_key = st.secrets["XAI_API_KEY"]

def elon_translator(text, context_type, subject=""):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    templates = {
        "targeted_motion": f"[motion: {subject} is ..., high-fidelity interaction]",
        "scene": "[scene: ..., cinematic environmental lighting]",
        "edit": "[clothing_edit: ..., preserving original pose 1:1]"
    }
    
    template = templates.get(context_type, "[...] ")
    prompt = f"Translate to technical tag for Memphis engine using format: {template}. Output ONLY resulting tag. Text: {text}"
    
    try:
        res = requests.post(url, headers=headers, json={
            "model": "grok-4-1-fast-non-reasoning", 
            "messages": [{"role": "user", "content": prompt}], 
            "temperature": 0.1
        })
        return res.json()['choices'][0]['message']['content']
    except: return f"[{context_type}: error]"

# --- 3. INTERFACE ---
st.title("🎥 RAWMOTION Director v8.9")
if "draft" not in st.session_state: st.session_state.draft = ""

# SIDEBAR
with st.sidebar:
    st.header("🎞️ Studio Setup")
    mode = st.radio("Tryb pracy:", ["🎬 Interactions (Duo/Trio)", "🪄 Magic Edit (1 Foto)"])
    st.divider()
    up_1 = st.file_uploader("Postać 1 (<IMAGE_1>):", type=['jpg','png','jpeg'])
    up_2 = st.file_uploader("Postać 2 (<IMAGE_2>):", type=['jpg','png','jpeg']) if "Interactions" in mode else None
    
    if st.button("✨ CZYŚĆ PROMPT"): st.session_state.draft = ""; st.rerun()
    if st.button("⏪ UNDO"): 
        st.session_state.draft = "\n".join(st.session_state.draft.strip().split("\n")[:-1]); st.rerun()

# PANEL REŻYSERSKI 3x2
c_img, c_tools = st.columns([1, 2])

with c_img:
    st.subheader("🖼️ Obsada")
    if up_1: st.image(up_1, caption="IMAGE_1", use_container_width=True)
    if up_2: st.image(up_2, caption="IMAGE_2", use_container_width=True)
    
    if st.button("👥 KROK 1: LOCK CHARACTERS", use_container_width=True):
        line = f"[character: <IMAGE_1> is person 1 on the left"
        if up_2: line += ", <IMAGE_2> is person 2 on the right"
        line += ". Preserve faces and bodies 1:1.]"
        st.session_state.draft += line + "\n"

with c_tools:
    if "Interactions" in mode:
        # Rząd 1
        r1_c1, r1_c2, r1_c3 = st.columns(3)
        with r1_c1:
            st.write("🎥 **Kamera**")
            cam_list = {
                "Auto (AI Director)": "AI wybiera ujęcie",
                "steady close-up": "Stabilne zbliżenie",
                "orbit 360": "Pełny obrót",
                "handheld shake": "Z ręki (dynamiczne)",
                "dolly zoom": "Najazd (Vertigo effect)",
                "low angle hero": "Z dołu (heroiczne)",
                "drone sweep": "Z góry (panoramiczne)",
                "whip pan": "Szybki przeskok",
                "slow motion zoom": "Powolny najazd",
                "static selfie": "Styl selfie"
            }
            cam_key = st.selectbox("Wybierz ujęcie:", list(cam_list.keys()), format_func=lambda x: f"{x} - {cam_list[x]}")
            if st.button("➕ Kamera"):
                tag = "[camera: AI selects best dynamic angle]" if "Auto" in cam_key else f"[camera: {cam_key}]"
                st.session_state.draft += tag + "\n"
        
        with r1_c2:
            st.write("🎙️ **Dialogi**")
            txt = st.text_input("Tekst:")
            who = st.selectbox("Mówi:", ["Osoba 1 (Lewa)", "Osoba 2 (Prawa)"])
            if st.button("➕ Głos"):
                p_id = who.split()[1]
                pos = "left" if p_id == "1" else "right"
                # POWRÓT DO 1.0s DLA EFEKTYWNOŚCI
                st.session_state.draft += f"[voice: polish person {p_id} on the {pos}] \"{txt}\" [pause: 1.0s]\n"
        
        with r1_c3:
            st.write("🕺 **Akcja Postaci**")
            subj = st.selectbox("Kto:", ["person 1", "person 2", "both together"])
            act_pl = st.text_input("Ruch (np. macha ręką):")
            if st.button("➕ Akcja"):
                st.session_state.draft += elon_translator(act_pl, "targeted_motion", subj) + "\n"

        st.divider()
        # Rząd 2
        r2_c1, r2_c2, r2_c3 = st.columns(3)
        with r2_c1:
            st.write("🌍 **Tło i Scena**")
            env = st.text_input("Gdzie są? (np. góry):")
            if st.button("➕ Scena"):
                st.session_state.draft += elon_translator(env, "scene") + "\n"
        with r2_c2:
            st.write("🎵 **Muzyka Tła**")
            bg_mus = st.selectbox("Styl:", ["None", "Cinematic Pop", "Romantic Piano", "Summer Chill", "Dark Tension", "Epic Orchestral"])
            if st.button("➕ Muzyka"):
                st.session_state.draft += f"[audio: background {bg_mus.lower()}]\n"
        with r2_c3:
            st.write("🔊 **Efekty SFX**")
            sfx = st.selectbox("SFX:", ["Laughter", "Applause", "Birds", "Beach waves", "City noise", "Heartbeat"])
            if st.button("➕ SFX"):
                st.session_state.draft += f"[audio: {sfx.lower()}]\n"

    else: # MAGIC EDIT
        edit_desc = st.text_area("Opisz zmianę (np. strój kąpielowy):")
        if st.button("🪄 Edytuj Foto"):
            st.session_state.draft = f"[character: <IMAGE_1> is same person] " + elon_translator(edit_desc, "edit")

# --- RENDER ENGINE ---
st.divider()
st.session_state.draft = st.text_area("🛠️ TWOJA OŚ CZASU (DRAFT):", value=st.session_state.draft, height=200)

c_res, c_dur = st.columns(2)
with c_res: res = st.selectbox("Jakość:", ["480p", "720p"], index=1)
with c_dur: dur = st.slider("Długość klipu (sekundy):", 1, 15, 10)

if st.button("🚀 WYPAL FINALNE DZIEŁO", type="primary", use_container_width=True):
    if not up_1: st.error("Wgraj zdjęcie!"); st.stop()
    with st.spinner(f"Silnik Memphis renderuje ({dur}s)..."):
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            client = xai_sdk.AsyncClient(api_key=api_key)
            refs = [f"data:image/jpeg;base64,{base64.b64encode(up_1.getvalue()).decode()}"]
            if up_2: refs.append(f"data:image/jpeg;base64,{base64.b64encode(up_2.getvalue()).decode()}")
            
            async def run():
                if "Magic Edit" in mode:
                    return await client.image.generate(model="grok-imagine-image-edit", prompt=st.session_state.draft, image_url=refs[0])
                else:
                    return await client.video.generate(
                        model="grok-imagine-video", 
                        prompt=st.session_state.draft, 
                        reference_image_urls=refs, 
                        duration=dur, 
                        resolution=res
                    )

            res_data = loop.run_until_complete(run())
            if "Magic Edit" in mode: st.image(res_data.url)
            else: st.video(requests.get(res_data.url).content)
            st.success("🎬 Gotowe!")
        except Exception as e: st.error(f"🔴 Błąd: {str(e)}")
