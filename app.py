import streamlit as st
import xai_sdk
import asyncio
import base64
import requests

# 1. Konfiguracja strony
st.set_page_config(page_title="RAWMOTION Studio PRO", layout="wide", page_icon="🎬")

# 2. Bezpieczne pobieranie klucza
try:
    api_key = st.secrets["XAI_API_KEY"]
except Exception:
    st.error("❌ BŁĄD: Nie znaleziono klucza 'XAI_API_KEY' w Secrets!")
    st.stop()

# --- FUNKCJE LOGICZNE (SYNCHRONICZNE WRAPPERY) ---

def get_translated_prompt(polish_text, api_key):
    async def _async_call():
        client = xai_sdk.AsyncClient(api_key=api_key)
        system_instr = (
            "You are a professional video prompting expert for Memphis (xAI). "
            "Convert the Polish description into a technical, cinematic English prompt. "
            "Use tags: [motion], [audio], [camera]. Keep Polish dialogues in [voice_left/right] tags. "
            "Add quality: 4k, realistic."
        )
        response = await client.chat.completions.create(
            model="grok-4-20-0309-non-reasoning",
            messages=[
                {"role": "system", "content": system_instr},
                {"role": "user", "content": polish_text}
            ]
        )
        return response.choices[0].message.content
    
    # Bezpieczne uruchomienie asynchroniczne wewnątrz Streamlita
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_async_call())

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
    return loop.run_until_complete(_async_call())

# --- INTERFEJS ---

st.title("🎬 RAWMOTION Studio PRO")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ Parametry")
    temp = st.slider("Temperatura:", 0.0, 2.0, 1.0, 0.1)
    duration = st.slider("Długość (s):", 5, 15, 6)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. Scenariusz")
    polish_input = st.text_area("Opisz scenę po polsku:", placeholder="Np. Chłopaki się śmieją...", height=100)
    
    if st.button("🪄 Przygotuj techniczny prompt (AI)", use_container_width=True):
        if polish_input:
            with st.spinner("Grok-4 analizuje Twój opis..."):
                try:
                    translated = get_translated_prompt(polish_input, api_key)
                    st.session_state['final_prompt'] = translated
                except Exception as e:
                    st.error(f"Błąd tłumaczenia: {e}")
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
            with st.spinner("Trwa renderowanie... (ok. 90-120s)"):
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
                        file_name="rawmotion_production.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"⚠️ Błąd renderu: {str(e)}")
        else:
            st.error("Wgraj zdjęcie i przygotuj prompt!")
