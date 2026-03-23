import streamlit as st
import xai_sdk
import asyncio
import base64

# Pobieranie klucza z bezpiecznych ustawień Streamlit
try:
    api_key = st.secrets["XAI_API_KEY"]
except:
    st.error("❌ Brak klucza API w Secrets!")
    st.stop()

st.title("🎬 RAWMOTION Studio")
st.write("Wgraj zdjęcie i ożyw je za pomocą silnika Elona.")

# Interfejs wgrywania pliku
uploaded_file = st.file_uploader("Wybierz zdjęcie (JPG/PNG)", type=['jpg', 'jpeg', 'png'])
user_prompt = st.text_area("Twój Prompt (scenariusz):", "Two men at a stadium, smiling and talking naturally.")
duration = st.slider("Długość (sekundy):", 5, 15, 5)

if st.button("🚀 Generuj Wideo"):
    if uploaded_file is not None:
        with st.spinner("Memphis pracuje... To potrwa od 60 do 120 sekund."):
            try:
                # Konwersja do base64 bezpośrednio z wrzuconego pliku
                bytes_data = uploaded_file.getvalue()
                b64_img = base64.b64encode(bytes_data).decode('utf-8')
                image_url = f"data:image/jpeg;base64,{b64_img}"

                # Silnik Elona
                client = xai_sdk.AsyncClient(api_key=api_key)
                
                # Uruchomienie asynchroniczne
                async def generate():
                    return await client.video.generate(
                        model="grok-imagine-video",
                        image_url=image_url,
                        prompt=user_prompt,
                        duration=duration,
                        aspect_ratio="16:9"
                    )
                
                video = asyncio.run(generate())
                
                st.success("🔥 MAMY TO!")
                st.video(video.url)
                st.write(f"Link do pobrania: {video.url}")

            except Exception as e:
                st.error(f"⚠️ Błąd: {e}")
    else:
        st.warning("Musisz najpierw wgrać zdjęcie!")
