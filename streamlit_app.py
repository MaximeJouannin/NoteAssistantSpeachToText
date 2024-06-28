import streamlit as st
from audio_recorder_streamlit import audio_recorder
import azure.cognitiveservices.speech as speechsdk
from openai import AzureOpenAI
import re
import tempfile
from io import BytesIO
from docx import Document
from pydub import AudioSegment
import threading
from PyPDF2 import PdfReader

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
    #st.write("Réponse GPT :", processed_text)
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
                #st.write("Synthèse vocale du texte réalisée pour : [{}]".format(text))
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    st.write("Détails de l'erreur : {}".format(cancellation_details.error_details))
    except Exception as e:
        st.write(f"Error during speech synthesis: {e}")

# Function to read text from a .docx file
def read_docx(file):
    doc = Document(file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)


# Function to extract text from a PDF file
# Fonction pour lire un fichier PDF
def read_pdf(file):
    pdf_reader = PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


# Function to handle different types of inputs and combine them
def handle_inputs(Audio_fromMicrophone,text_input,uploaded_Audiofile,doc_file):
    combined_input = []         
    if Audio_fromMicrophone:
        # Save the audio bytes to a temporary WAV file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(Audio_fromMicrophone)
            st.session_state.audio_file = tmp_file.name

        st.audio(Audio_fromMicrophone, format="audio/wav")
        
        if st.session_state.audio_file:
            st.write(f"Processing audio file: {st.session_state.audio_file}")
            recognized_text = recognize_audio_file(st.session_state.audio_file)
            st.session_state.recognized_text = recognized_text
            # process_and_synthesize_text(st.session_state.recognized_text)
            combined_input.append('[Entrée vocale]\n\n'+ recognized_text +'\n\n[Fin entrée vocale ]')
        
    if text_input:
        combined_input.append('[Entrée texte utilisateur]\n\n' + text_input + '\n\n[Fin entrée texte utilisateur]')
    
    if uploaded_Audiofile:
        file_extension = uploaded_Audiofile.name.split(".")[-1]
        if file_extension == "mp3":
            try:
                audio = AudioSegment.from_file(BytesIO(uploaded_Audiofile.read()), format="mp3")
                wav_path = "temp_audio_file.wav"
                audio.export(wav_path, format="wav")
            except Exception as e:
                print(f"Error converting file: {str(e)}")    
        else:
            wav_path = "temp_audio_file.wav"
            with open(wav_path, "wb") as f:
                f.write(uploaded_Audiofile.read())

        audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
        speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        result = speech_recognizer.recognize_once()
        # st.write("Texte reconnu : {}".format(result.text))
        combined_input.append('[Entrée fichier audio]\n\n' + result.text + '\n\n[Fin entrée audio]')
           
            
    if doc_file:
        text=""
        # Read the content of the uploaded file
        # Lecture et concaténation du contenu des fichiers
        for uploaded_file in doc_file:
            if uploaded_file.type == "text/plain":
                text +=  uploaded_file.name +'\n'+ uploaded_file.read().decode("utf-8") + '\n\n'
            elif uploaded_file.type == "application/pdf":
                text += uploaded_file.name +'\n'+ read_pdf(uploaded_file) + "\n\n"
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text += uploaded_file.name +'\n'+ read_docx(uploaded_file) + "\n\n"
        combined_input.append('[Entrée doc]\n\n' +text+'\n\n[Fin entrée doc]')
        
    return '\n'.join(combined_input)

def page1():
    
    # Streamlit UI
    st.title('OpenAI Text Generation with Multiple Inputs')
    
    st.subheader("Application de reconnaissance et de traitement vocal")

    # Record audio
    audio_bytes = audio_recorder(text="Click to record", pause_threshold=2.0)
    
    # Text input area for user to enter text
    user_text_input = st.text_area("Enter your text here:", key="text_input")

    # File uploader for audio files
    uploaded_Audiofile = st.file_uploader('Choisir un fichier audio :vhs:', type=["wav", "mp3"])
    
    # File uploaders for documents
    uploaded_doc_file = st.file_uploader('Upload a document 📥', type=["txt", "docx", "pdf"], accept_multiple_files=True)
    
    combined_input = handle_inputs(audio_bytes,user_text_input,uploaded_Audiofile, uploaded_doc_file)
    edit_combined_text_input = st.text_area("Text combined:", value=combined_input,key="combined_text_input",height=200)

    # Button to trigger text processing
    if st.button("Generate Resume"):
        if edit_combined_text_input:
            process_and_synthesize_text(edit_combined_text_input)
        else:
            st.warning("Please provide some input.")
            
    # Play the synthesized speech if available
    if st.session_state.synthesized_audio_file:
        st.audio(st.session_state.synthesized_audio_file, format="audio/wav", autoplay=True)
        
def page2():
    # Streamlit UI
    st.subheader('')
    
    
st.sidebar.title('Navigation')
selection = st.sidebar.radio("Go to", ['Multiple Inputs', 'Traitement vocal'])

if selection == 'Multiple Inputs':
    page1()
elif selection == 'Traitement vocal':
    page2()
