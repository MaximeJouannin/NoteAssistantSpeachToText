import streamlit as st
import azure.cognitiveservices.speech as speechsdk
from openai import AzureOpenAI
import re

# Azure and OpenAI credentials
API_KEY = "45597a66237d464faebe8745618f5717"
RESOURCE_ENDPOINT = "https://inetum-open-ai-eastus.openai.azure.com/"

SPEECH_KEY = 'b48d398ec76644b985c461fd41e6df78'
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
chunks = []

def recognize_from_microphone_continuous():
    print("Starting continuous recognition...")

    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_config.speech_recognition_language = lang
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    def recognized_callback(evt):
        global chunks
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            chunks.append(evt.result.text)
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

    recognizer.start_continuous_recognition()
    print("Recognition started and listening continuously...")

    while st.session_state.recognition_active:
        if chunks:
            for chunk in chunks:
                st.session_state.recognized_text += f" {chunk}"
                print(f"UI Updated with text: {chunk}")
            chunks.clear()
            st.experimental_rerun()

    recognizer.stop_continuous_recognition()
    print("Recognition stopped.")

def process_and_synthesize_text(recognized_text):
    print(f"Processing and synthesizing text: {recognized_text}")
    processed_text = process_text_with_gpt(recognized_text)
    st.write("Réponse GPT :", processed_text)
    synthesize_speech(processed_text)

def start_recognition():
    st.session_state.recognition_active = True
    recognize_from_microphone_continuous()

def stop_recognition():
    st.session_state.recognition_active = False
    st.experimental_rerun()
    print("Recognition stopped.")

def process_text_with_gpt(recognized_text):
    client = AzureOpenAI(api_key=API_KEY, azure_endpoint=RESOURCE_ENDPOINT, api_version="2023-05-15")
    responsegpt = client.chat.completions.create(
        model="inetum-gpt-35-turbo-0613",
        messages=[
            {"role": "system", "content": "You are an assistant. Answer in " + lang},
            {"role": "user", "content": recognized_text}
        ]
    )
    text = responsegpt.choices[0].message.content
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

if st.session_state.recognition_active:
    if st.button('Arrêter la reconnaissance'):
        stop_recognition()
else:
    if st.button('Démarrer la reconnaissance'):
        start_recognition()

if re.search(r"\blance le traitement\b", st.session_state.recognized_text, re.IGNORECASE) and not st.session_state.processing_triggered:
    st.session_state.processing_triggered = True
    process_and_synthesize_text(st.session_state.recognized_text)

# Afficher le texte reconnu
st.write("Texte reconnu :", st.session_state.recognized_text)
