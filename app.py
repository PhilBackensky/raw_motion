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
    payload = {
        "model": "grok-4-1-fast-non-reasoning", # Używamy najszybszej wersji z Twojej listy
        "messages": [
            {
                "role": "system",
                "content": "Jesteś ekspertem od promptingu wideo dla Memphis. Zamień polski opis na techniczny prompt po angielsku z tagami [motion], [audio], [camera]. Polskie dialogi zachowaj w tagach [voice: polish]."
            },
            {"role": "user", "content": polish_text}
        ]
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        # Próba alternatywnej nazwy, jeśli fast nie wejdzie
        payload["model"] = "grok-beta"
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        raise Exception(f"Błąd API: {response.status_code} - {response.text}")

def get_video(api_key, img_b64, prompt, duration, temp):
    async def _async_call():
        client = xai_sdk.AsyncClient(api_key=api_key)
        return await client.video.generate(
            model="grok-imagine-video",
            image_url=img_b64,
            prompt=prompt,
            duration=duration,
            temperature=temp,
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

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. Scenariusz")
    polish_input = st.text_area("Opisz scenę po polsku:", placeholder="Np. Kobieta mówi: Wojtek, chcesz?...", height=100)
    
    if st.button("🪄 Przygotuj techniczny prompt (AI)", use_container_width=True):
        if polish_input:
            with st.spinner("Grok-4-Fast analizuje Twój opis..."):
                try:
                    translated = get_translated_prompt(polish_input, api_key)
                    st.session_state['final_prompt'] = translated
                except Exception as e:
                    st.error(f"⚠️ Błąd połączenia: {e}")
        else:
            st.warning("Wpisz opis!")

    final_prompt = st.text_area(
        "Finalny Prompt (możesz edytować):", 
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
