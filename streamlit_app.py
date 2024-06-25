import streamlit as st
import azure.cognitiveservices.speech as speechsdk
import openai
import threading

# Azure and OpenAI credentials
API_KEY = "45597a66237d464faebe8745618f5717"
RESOURCE_ENDPOINT = "https://inetum-open-ai-eastus.openai.azure.com/"
openai.api_type = "azure"
openai.api_key = API_KEY
openai.api_base = RESOURCE_ENDPOINT
openai.api_version = "2023-05-15"

SPEECH_KEY = '28e83bb343234fdab27caa36e79fe5b3'
SPEECH_REGION = 'francecentral'
lang = "fr-FR"

# Initialize session state
if 'recognition_active' not in st.session_state:
    st.session_state.recognition_active = False
if 'recognized_text' not in st.session_state:
    st.session_state.recognized_text = ""
if 'show_start_button' not in st.session_state:
    st.session_state.show_start_button = True
if 'show_stop_button' not in st.session_state:
    st.session_state.show_stop_button = False

# Global variables
stop_event = threading.Event()
recognition_thread = None

def recognize_from_microphone():
    print("Starting recognition...")
    
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_config.speech_recognition_language = lang
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    
    result = recognizer.recognize_once_async().get()
    
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        recognized_text = result.text
        print(f"Recognized: {recognized_text}")
        st.session_state.recognized_text = recognized_text
        process_and_synthesize_text(recognized_text)
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized.")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Speech Recognition canceled: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation_details.error_details}")
    
    stop_event.set()
    st.session_state.recognition_active = False
    st.session_state.show_start_button = True
    st.session_state.show_stop_button = False

def process_and_synthesize_text(recognized_text):
    processed_text = process_text_with_gpt(recognized_text)
    st.write("Réponse GPT :", processed_text)
    synthesize_speech(processed_text)

def start_recognition():
    global recognition_thread
    stop_event.clear()
    st.session_state.recognition_active = True
    
    recognition_thread = threading.Thread(target=recognize_from_microphone)
    recognition_thread.start()
    st.session_state.show_start_button = False
    st.session_state.show_stop_button = True

def stop_recognition():
    print("Setting stop event...")
    stop_event.set()
    if recognition_thread is not None:
        recognition_thread.join()
        print("Recognition thread joined.")
    st.session_state.show_start_button = True
    st.session_state.show_stop_button = False

def process_text_with_gpt(recognized_text):
    responsegpt = openai.ChatCompletion.create(
        engine="inetum-gpt-35-turbo-0613",
        messages=[
            {"role": "system", "content": "You are an assistant. Answer in " + lang},
            {"role": "user", "content": recognized_text}
        ]
    )
    text = responsegpt['choices'][0]['message']['content']
    st.write(f"GPT Response: {text}")
    return text

def synthesize_speech(text):
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
    speech_config.speech_synthesis_voice_name = 'fr-FR-DeniseNeural'
    result = speech_synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        st.write("Synthèse vocale du texte réalisée pour : [{}]".format(text))
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        st.write("Synthèse vocale annulée : {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            st.write("Détails de l'erreur : {}".format(cancellation_details.error_details))

# Streamlit UI
st.title("Application de reconnaissance et de traitement vocal")

col1, col2 = st.columns(2)
col1.button('Démarrer la reconnaissance', on_click=start_recognition, disabled=st.session_state.show_stop_button)
col2.button('Arrêter la reconnaissance', on_click=stop_recognition, disabled=st.session_state.show_start_button)

if st.session_state.recognized_text:
    st.write("Texte reconnu :", st.session_state.recognized_text)
    process_and_synthesize_text(st.session_state.recognized_text)
    st.session_state.recognized_text = ""

# File uploader for audio files
uploaded_file = st.file_uploader("Choisir un fichier audio", type=["wav", "mp3"])
if uploaded_file is not None:
    file_extension = uploaded_file.name.split(".")[-1]
    if file_extension == "mp3":
        audio = AudioSegment.from_file(BytesIO(uploaded_file.read()), format="mp3")
        wav_path = "temp_audio_file.wav"
        audio.export(wav_path, format="wav")
    else:
        wav_path = "temp_audio_file.wav"
        with open(wav_path, "wb") as f:
            f.write(uploaded_file.read())

    audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    result = speech_recognizer.recognize_once()
    st.write("Texte reconnu : {}".format(result.text))

    processed_text = process_text_with_gpt(result.text)
    st.write("Réponse GPT :", processed_text)
    synthesize_speech(processed_text)
