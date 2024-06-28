import streamlit as st
from audio_recorder_streamlit import audio_recorder
import azure.cognitiveservices.speech as speechsdk
from openai import AzureOpenAI
import re
import tempfile

# Azure and OpenAI credentials
API_KEY = "45597a66237d464faebe8745618f5717"
RESOURCE_ENDPOINT = "https://inetum-open-ai-eastus.openai.azure.com/"
SPEECH_KEY = 'b48d398ec76644b985c461fd41e6df78'
SPEECH_REGION = 'francecentral'
lang = "fr-FR"

# Initialize session state
if 'recognized_text' not in st.session_state:
    st.session_state.recognized_text = ""
if 'audio_file' not in st.session_state:
    st.session_state.audio_file = None
if 'synthesized_audio_file' not in st.session_state:
    st.session_state.synthesized_audio_file = None

def recognize_audio_file(file_path):
    st.write(f"Recognizing audio file: {file_path}")
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_config.speech_recognition_language  = lang
    audio_config = speechsdk.audio.AudioConfig(filename=file_path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        st.write(f"Recognized: {result.text}")
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        st.write("No speech could be recognized")
        return "No speech could be recognized"
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        st.write(f"CANCELED: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            st.write(f"Error details: {cancellation_details.error_details}")
            return f"Error: {cancellation_details.error_details}"
        return "Recognition canceled"

def process_and_synthesize_text(recognized_text):
    processed_text = process_text_with_gpt(recognized_text)
    st.write("Réponse GPT :", processed_text)
    synthesize_speech(processed_text)

def process_text_with_gpt(recognized_text):
    try:
        client = AzureOpenAI(api_key=API_KEY, azure_endpoint=RESOURCE_ENDPOINT, api_version="2023-05-15")
        responsegpt = client.chat.completions.create(
            model="inetum-gpt-35-turbo-0613",
            messages=[
                {"role": "system", "content": "You are an assistant. Answer in " + lang},
                {"role": "user", "content": recognized_text}
            ]
        )
        text = responsegpt.choices[0].message.content
        st.write(f"GPT Response: {text}")
        return text
    except Exception as e:
        st.write(f"Error processing text with GPT: {e}")
        return "Error processing text with GPT"

def synthesize_speech(text):
    try:
        speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
        speech_config.speech_synthesis_language = lang
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            audio_config = speechsdk.audio.AudioOutputConfig(filename=tmp_file.name)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            result = synthesizer.speak_text_async(text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                st.session_state.synthesized_audio_file = tmp_file.name
                st.write("Synthèse vocale du texte réalisée pour : [{}]".format(text))
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    st.write("Détails de l'erreur : {}".format(cancellation_details.error_details))
    except Exception as e:
        st.write(f"Error during speech synthesis: {e}")

# Streamlit UI
st.title("Application de reconnaissance et de traitement vocal")

# Record audio
audio_bytes = audio_recorder(text="Click to record", pause_threshold=2.0)

if audio_bytes:
    # Save the audio bytes to a temporary WAV file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_bytes)
        st.session_state.audio_file = tmp_file.name

    st.audio(audio_bytes, format="audio/wav")
    
    if st.session_state.audio_file:
        st.write(f"Processing audio file: {st.session_state.audio_file}")
        recognized_text = recognize_audio_file(st.session_state.audio_file)
        st.session_state.recognized_text = recognized_text
        process_and_synthesize_text(st.session_state.recognized_text)

# Display the recognized text
st.write("Texte reconnu :", st.session_state.recognized_text)

# Play the synthesized speech if available
if st.session_state.synthesized_audio_file:
    st.audio(st.session_state.synthesized_audio_file, format="audio/wav", autoplay=True)
