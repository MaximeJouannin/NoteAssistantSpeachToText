import streamlit as st
import azure.cognitiveservices.speech as speechsdk
import openai
import queue
import time
import threading
import re

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
if 'recognized_text' not in st.session_state:
    st.session_state.recognized_text = ""
if 'recognition_active' not in st.session_state:
    st.session_state.recognition_active = False
if 'processing_triggered' not in st.session_state:
    st.session_state.processing_triggered = False

# Global variables
text_queue = queue.Queue()
stop_event = threading.Event()

def recognize_from_microphone_continuous():
    print("Starting continuous recognition...")

    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_config.speech_recognition_language = lang
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    def recognized_callback(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            text_queue.put(evt.result.text)
            print(f"Recognized: {evt.result.text}")

    def recognizing_callback(evt):
        print(f"Recognizing: {evt.result.text}")

    def session_started(evt):
        print(f"SESSION STARTED: {evt.session_id}")

    def session_stopped(evt):
        print(f"SESSION STOPPED: {evt.session_id}")

    def canceled_callback(evt):
        cancellation_details = evt.result.cancellation_details
        print(f"CANCELED: {evt.result.reason}")
        print(f"CANCELLATION REASON: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"CANCELLATION ERROR DETAILS: {cancellation_details.error_details}")

    recognizer.recognized.connect(recognized_callback)
    recognizer.recognizing.connect(recognizing_callback)
    recognizer.session_started.connect(session_started)
    recognizer.session_stopped.connect(session_stopped)
    recognizer.canceled.connect(canceled_callback)

    recognizer.start_continuous_recognition_async()

    print("Recognition started and listening continuously...")

    while not stop_event.is_set():
        time.sleep(0.1)

    recognizer.stop_continuous_recognition_async().get()
    print("Recognition stopped.")

def process_and_synthesize_text(recognized_text):
    print(f"Processing and synthesizing text: {recognized_text}")
    processed_text = process_text_with_gpt(recognized_text)
    st.write("Réponse GPT :", processed_text)
    synthesize_speech(processed_text)

def start_recognition():
    global stop_event
    stop_event.clear()
    st.session_state.recognition_active = True
    recognition_thread = threading.Thread(target=recognize_from_microphone_continuous)
    recognition_thread.start()

def stop_recognition():
    global stop_event
    print("Stopping recognition...")
    stop_event.set()
    st.session_state.recognition_active = False
    print("Recognition stopped.")

def process_text_with_gpt(recognized_text):
    responsegpt = openai.ChatCompletion.create(
        engine="inetum-gpt-35-turbo-0613",
        messages=[
            {"role": "system", "content": "You are an assistant. Answer in " + lang},
            {"role": "user", "content": recognized_text}
        ]
    )
    text = responsegpt['choices'][0]['message']['content']
    print(f"GPT Response: {text}")
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

if not st.session_state.recognition_active:
    if st.button('Démarrer la reconnaissance'):
        start_recognition()

if st.session_state.recognition_active:
    if st.button('Arrêter la reconnaissance'):
        stop_recognition()

# Mettre à jour l'interface utilisateur avec le texte reconnu
if 'recognition_active' in st.session_state and st.session_state.recognition_active:
    while not text_queue.empty():
        text = text_queue.get()
        st.session_state.recognized_text += f" {text}"
        print(f"UI Updated with text: {text}")

if re.search(r"\blance le traitement\b", st.session_state.recognized_text, re.IGNORECASE) and not st.session_state.processing_triggered:
    st.session_state.processing_triggered = True
    process_and_synthesize_text(st.session_state.recognized_text)

# Afficher le texte reconnu
st.write("Texte reconnu :", st.session_state.recognized_text)
