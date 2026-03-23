import streamlit as st
import xai_sdk
import asyncio
import base64
import requests
import json

# 1. Konfiguracja strony
st.set_page_config(page_title="RAWMOTION Studio PRO", layout="wide", page_icon="🎬")

# 2. Bezpieczne pobieranie klucza
try:
    api_key = st.secrets["XAI_API_KEY"]
except Exception:
    st.error("❌ BŁĄD: Nie znaleziono klucza 'XAI_API_KEY' w Secrets!")
    st.stop()

# --- FUNKCJE LOGICZNE ---

def get_translated_prompt(polish_text, api_key):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    # Ta instrukcja wymusza na AI wyciąganie tekstu mówionego
    system_instr = (
        "You are a technical director for Memphis video engine. "
        "CONVERT Polish input into a strict technical prompt. "
        "STRICT RULES: "
        "1. Identify any spoken text in Polish (even if not in quotes). "
        "2. Place that Polish text EXACTLY inside [voice: polish] tags. "
        "3. Describe movement with [motion] tags (e.g., [motion: woman speaks, smiling and winking]). "
        "4. DO NOT ignore the actual words spoken. "
        "5. Final output must be English technical description + Polish speech tags."
    )
    payload = {
        "model": "grok-4-1-fast-non-reasoning",
        "messages": [
            {"role": "system", "content": system_instr},
            {"role": "user", "content": polish_text}
        ],
        "temperature": 0.3 # Niższa temperatura tłumacza = większa dosłowność
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"Błąd API: {response.status_code} - {response.text}"

def get_video(api_key, img_b64, prompt, duration, temp):
    async def _async_call():
        client = xai_sdk.AsyncClient(api_key=api_key)
        # Usunęliśmy 'temperature', bo SDK go aktualnie nie rozpoznaje
        return await client.video.generate(
            model="grok-imagine-video",
            image_url=img_b64,
            prompt=prompt,
            duration=duration,
            aspect_ratio="16:9"
        )
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_async_call())
    finally:
        loop.close()

# --- INTERFEJS ---

st.title("🎬 RAWMOTION Studio PRO")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ Parametry")
    temp = st.slider("Temperatura (Odjechanie):", 0.0, 2.0, 1.0, 0.1)
    duration = st.slider("Długość (s):", 5, 15, 6)
    st.info("Dla mowy trzymaj ok. 1.0 dla realizmu.")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. Scenariusz")
    polish_input = st.text_area("Opisz scenę po polsku:", placeholder="Np. Kobieta mówi: Wojtek, chcesz? To masz! (i mruga okiem)", height=100)
    
    if st.button("🪄 Przygotuj techniczny prompt (AI)", use_container_width=True):
        if polish_input:
            with st.spinner("Grok-4-Fast składa scenariusz..."):
                try:
                    translated = get_translated_prompt(polish_input, api_key)
                    st.session_state['final_prompt'] = translated
                except Exception as e:
                    st.error(f"⚠️ Błąd: {e}")
        else:
            st.warning("Wpisz opis!")

    final_prompt = st.text_area(
        "Finalny Prompt (edytuj jeśli brakuje [voice]):", 
        value=st.session_state.get('final_prompt', ""), 
        height=180
    )
    
    st.subheader("2. Materiał źródłowy")
    uploaded_file = st.file_uploader("Wgraj zdjęcie:", type=['jpg', 'jpeg', 'png'])

with col2:
    st.subheader("3. Render i Wynik")
    
    if st.button("🚀 WYPAL WIDEO", use_container_width=True, type="primary"):
        if uploaded_file and final_prompt:
            with st.spinner("Trwa renderowanie w Memphis..."):
                try:
                    img_bytes = uploaded_file.getvalue()
                    b64_img = base64.b64encode(img_bytes).decode('utf-8')
                    full_img_url = f"data:image/jpeg;base64,{b64_img}"
                    
                    video_obj = get_video(api_key, full_img_url, final_prompt, duration, temp)
                    
                    video_res = requests.get(video_obj.url)
                    video_data = video_res.content
                    
                    st.video(video_data)
                    st.download_button(
                        label="💾 POBIERZ PLIK MP4",
                        data=video_data,
                        file_name="rawmotion_export.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"⚠️ Błąd renderu: {str(e)}")
        else:
            st.error("Wgraj zdjęcie i przygotuj prompt!")

st.markdown("---")
