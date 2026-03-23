import streamlit as st
import xai_sdk
import asyncio
import base64
import requests

# 1. Konfiguracja strony
st.set_page_config(page_title="RAWMOTION Studio PRO", layout="wide", page_icon="🎬")

# 2. Bezpieczne pobieranie klucza z Secrets Streamlita
try:
    api_key = st.secrets["XAI_API_KEY"]
except Exception:
    st.error("❌ BŁĄD: Nie znaleziono klucza 'XAI_API_KEY' w Settings -> Secrets!")
    st.stop()

# --- FUNKCJE LOGICZNE ---

# Funkcja tłumacząca polski opis na techniczny prompt Memphis (Grok-4)
async def translate_to_memphis(polish_text, api_key):
    client = xai_sdk.AsyncClient(api_key=api_key)
    system_instr = (
        "Jesteś profesjonalnym reżyserem i ekspertem od promptingu wideo dla modelu Memphis (xAI). "
        "Twoim zadaniem jest zamiana polskiego opisu użytkownika na techniczny, kinowy prompt po angielsku. "
        "Używaj tagów: [motion] dla ruchu, [audio] dla dźwięku, [camera] dla pracy kamery. "
        "Jeśli użytkownik podaje dialogi, zachowaj je w oryginalnym języku polskim w tagach głosowych (np. [voice_left]). "
        "Dodaj parametry jakościowe: 4k, highly detailed, realistic textures."
    )
    
    response = await client.chat.completions.create(
        model="grok-4-20-0309-non-reasoning",
        messages=[
            {"role": "system", "content": system_instr},
            {"role": "user", "content": polish_text}
        ]
    )
    return response.choices[0].message.content

# Główna funkcja generująca wideo
async def generate_video(api_key, img_b64, prompt, duration, temp):
    client = xai_sdk.AsyncClient(api_key=api_key)
    return await client.video.generate(
        model="grok-imagine-video",
        image_url=img_b64,
        prompt=prompt,
        duration=duration,
        temperature=temp,
        aspect_ratio="16:9"
    )

# --- INTERFEJS UŻYTKOWNIKA ---

st.title("🎬 RAWMOTION Studio PRO")
st.markdown("---")

# Pasek boczny z ustawieniami
with st.sidebar:
    st.header("⚙️ Parametry Silnika")
    temp = st.slider("Temperatura (Odjechanie):", 0.0, 2.0, 1.0, 0.1)
    duration = st.slider("Długość filmu (sekundy):", 5, 15, 5)
    st.divider()
    st.info("Wyższa temperatura = większa kreatywność i chaos. 1.0 to standard.")

# Układ kolumn: Lewa (Input) | Prawa (Podgląd)
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. Scenariusz")
    polish_input = st.text_area("Opisz scenę po polsku:", placeholder="Np. Dwóch facetów na stadionie śmieje się do łez, jeden pokazuje palcem na drugiego...", height=100)
    
    if st.button("🪄 Przygotuj techniczny prompt (AI)", use_container_width=True):
        if polish_input:
            with st.spinner("Grok-4 analizuje Twój opis..."):
                translated = asyncio.run(translate_to_memphis(polish_input, api_key))
                st.session_state['final_prompt'] = translated
        else:
            st.warning("Wpisz najpierw opis po polsku!")

    # Pole edycji finalnego promptu
    final_prompt = st.text_area(
        "Finalny Prompt Memphis (możesz go edytować):", 
        value=st.session_state.get('final_prompt', ""), 
        height=180
    )
    
    st.subheader("2. Materiał źródłowy")
    uploaded_file = st.file_uploader("Wgraj zdjęcie (JPG/PNG):", type=['jpg', 'jpeg', 'png'])

with col2:
    st.subheader("3. Render i Wynik")
    
    if st.button("🚀 WYPAL WIDEO", use_container_width=True, type="primary"):
        if uploaded_file and final_prompt:
            with st.spinner("Trwa renderowanie w Memphis... (ok. 90-120s)"):
                try:
                    # Konwersja zdjęcia do base64
                    img_bytes = uploaded_file.getvalue()
                    b64_img = base64.b64encode(img_bytes).decode('utf-8')
                    full_img_url = f"data:image/jpeg;base64,{b64_img}"
                    
                    # Generowanie
                    video_obj = asyncio.run(generate_video(api_key, full_img_url, final_prompt, duration, temp))
                    
                    # Pobieranie pliku do pamięci apki (Auto-Download logic)
                    video_res = requests.get(video_obj.url)
                    video_data = video_res.content
                    
                    st.video(video_data)
                    
                    st.download_button(
                        label="💾 POBIERZ PLIK MP4 NA DYSK",
                        data=video_data,
                        file_name="rawmotion_production.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
                    st.success("Wideo wygenerowane pomyślnie!")
                    
                except Exception as e:
                    st.error(f"⚠️ Błąd silnika: {str(e)}")
        else:
            st.error("Błąd: Musisz mieć wgrane zdjęcie ORAZ przygotowany prompt!")

st.markdown("---")
st.caption("Powered by xAI Memphis Engine & Streamlit. Created by PhilBackensky.")
