import streamlit as st
import azure.cognitiveservices.speech as speechsdk
import openai
import time
import os
from pydub import AudioSegment
from io import BytesIO

# Azure and OpenAI credentials
API_KEY = "45597a66237d464faebe8745618f5717"
RESOURCE_ENDPOINT = "https://inetum-open-ai-eastus.openai.azure.com/"
openai.api_type = "azure"
openai.api_key = API_KEY
openai.api_base = RESOURCE_ENDPOINT
openai.api_version = "2023-05-15"

SPEECH_KEY = '17dcc6db4f1b496b8cf4baffacbbe598'
SPEECH_REGION = 'westeurope'

lang = "fr-FR"

# Initialize session state
if 'recognition_active' not in st.session_state:
    st.session_state.recognition_active = False
if 'recognized_text' not in st.session_state:
    st.session_state.recognized_text = ""

# Function to recognize speech from microphone continuously
def recognize_from_microphone_continuous(lang):
    st.write("Starting continuous recognition...")
    print("Starting continuous recognition...")
    
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_config.speech_recognition_language = lang
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    
    all_results = []
    def handle_final_result(evt):
        all_results.append(evt.result.text)
        st.write(f"Recognized (intermediate): {evt.result.text}")
        print(f"Recognized (intermediate): {evt.result.text}")

    speech_recognizer.recognized.connect(handle_final_result)
    speech_recognizer.start_continuous_recognition()

    st.write("Recognition started. Waiting for stop signal...")
    print("Recognition started. Waiting for stop signal...")

    while st.session_state.recognition_active:
        time.sleep(0.1)  # Small delay to prevent a busy-wait loop

    st.write("Stopping continuous recognition...")
    print("Stopping continuous recognition...")
    speech_recognizer.stop_continuous_recognition()
    
    recognized_text = " ".join(all_results)
    st.write(f"Recognized (final): {recognized_text}")
    print(f"Recognized (final): {recognized_text}")
    
    return recognized_text

# Function to process recognized text with OpenAI GPT
def process_text_with_gpt(recognized_text):
    st.write(f"Processing text with GPT: {recognized_text}")
    print(f"Processing text with GPT: {recognized_text}")
    
    responsegpt = openai.ChatCompletion.create(
        engine="inetum-gpt-35-turbo-0613", # engine = "deployment_name".
        messages=[
            {"role": "system", "content": "You are an assistant and you always need to answer even if you don't know a correct answer. For every message you add to the message the equivalent sentiment carried by the message. You also suggest a matching bodily animation. Answer in " + lang},
            {"role": "user", "content": recognized_text}        
        ]
    )

    text = responsegpt['choices'][0]['message']['content']
    st.write(f"GPT Response: {text}")
    print(f"GPT Response: {text}")
    return text

# Function to synthesize speech
def synthesize_speech(text):
    st.write(f"Synthesizing speech for text: {text}")
    print(f"Synthesizing speech for text: {text}")
    
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

    speech_config.speech_synthesis_voice_name = 'fr-FR-DeniseNeural'
    result = speech_synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        st.write("Synthèse vocale du texte réalisée pour : [{}]".format(text))
        print("Synthèse vocale du texte réalisée pour : [{}]".format(text))
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        st.write("Synthèse vocale annulée : {}".format(cancellation_details.reason))
        print("Synthèse vocale annulée : {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            st.write("Détails de l'erreur : {}".format(cancellation_details.error_details))
            print("Détails de l'erreur : {}".format(cancellation_details.error_details))

# Function to convert MP3 to WAV
def convert_mp3_to_wav(mp3_data):
    st.write("Converting MP3 to WAV")
    print("Converting MP3 to WAV")
    
    audio = AudioSegment.from_file(BytesIO(mp3_data), format="mp3")
    wav_path = "temp_audio_file.wav"
    audio.export(wav_path, format="wav")
    
    st.write("Conversion complete")
    print("Conversion complete")
    
    return wav_path

# Streamlit UI
st.title("Application de reconnaissance et de traitement vocal")

# Start recognition button
if not st.session_state.recognition_active and not st.session_state.recognized_text:
    if st.button("Démarrer la reconnaissance"):
        st.write("Recognition started by user.")
        print("Recognition started by user.")
        
        st.session_state.recognition_active = True
        st.experimental_rerun()

# Stop recognition button
if st.session_state.recognition_active:
    if st.button("Arrêter la reconnaissance"):
        st.write("Recognition stopped by user.")
        print("Recognition stopped by user.")
        
        st.session_state.recognition_active = False
        st.session_state.recognized_text = recognize_from_microphone_continuous(lang)
        
        st.write(f"Recognized Text: {st.session_state.recognized_text}")
        print(f"Recognized Text: {st.session_state.recognized_text}")
        
        st.experimental_rerun()

# Display and process recognized text
if st.session_state.recognized_text:
    st.write("Processing the recognized text...")
    print("Processing the recognized text...")
    
    st.write("Texte reconnu final :", st.session_state.recognized_text)
    processed_text = process_text_with_gpt(st.session_state.recognized_text)
    
    st.write("Réponse GPT :", processed_text)
    synthesize_speech(processed_text)
    
    st.write("Clearing recognized text after processing.")
    print("Clearing recognized text after processing.")
    
    # Clear the recognized text after processing
    st.session_state.recognized_text = ""

# File uploader for audio files
uploaded_file = st.file_uploader("Choisir un fichier audio", type=["wav", "mp3"])
if uploaded_file is not None:
    st.write("File uploaded by user.")
    print("File uploaded by user.")
    
    file_extension = uploaded_file.name.split(".")[-1]
    if file_extension == "mp3":
        wav_path = convert_mp3_to_wav(uploaded_file.read())
    else:
        wav_path = "temp_audio_file.wav"
        with open(wav_path, "wb") as f:
            f.write(uploaded_file.read())

    audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    result = speech_recognizer.recognize_once()
    st.write("Texte reconnu : {}".format(result.text))
    print("Texte reconnu : {}".format(result.text))

    processed_text = process_text_with_gpt(result.text)
    st.write("Réponse GPT :", processed_text)
    synthesize_speech(processed_text)
