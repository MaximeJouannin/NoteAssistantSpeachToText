import streamlit as st
import azure.cognitiveservices.speech as speechsdk
import openai
import threading

import fitz  # PyMuPDF library for working with PDF files
from io import BytesIO
from docx import Document
from pydub import AudioSegment



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
    # st.write(f"GPT Response: {text}")
    return text

def synthesize_speech(text):
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
    speech_config.speech_synthesis_voice_name = 'fr-FR-DeniseNeural'
    result = speech_synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        st.write("Synthèse vocale du texte réalisée pour : \n\n {}".format(text))
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        st.write("Synthèse vocale annulée : {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            st.write("Détails de l'erreur : {}".format(cancellation_details.error_details))


# Function to read text from a .docx file
def read_docx(file):
    doc = Document(file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)


# Function to extract text from a PDF file
def read_pdf(file):
    doc = fitz.open(file.name)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


# Function to handle different types of inputs and combine them
def handle_inputs(text_input,doc_file):
    combined_input = []
    if text_input:
        combined_input.append(text_input)
    if doc_file:
        # Read the content of the uploaded file
        file_extension = doc_file.name.split(".")[-1]
        if file_extension == "txt":
            text = doc_file.getvalue().decode("utf-8")
        elif file_extension == "docx":
            text = read_docx(doc_file)
        elif file_extension == "pdf":
            text = read_pdf(doc_file)
        combined_input.append(text)

    return '\n'.join(combined_input)


#########################################################################################
# st.title('Dynamic Text Area Example')  
# # Input text area
# input_text = st.text_area('Input Text Area', height=100)

# def update_output_text(input_text):
#     # Here you can add any logic to process input_text and generate output_text
#     return input_text  # Example: Convert input to uppercase

# # Reactively update the output_text based on input_text changes
# output_text = update_output_text(input_text)
# # Display output text inside a text area
# edited_text = st.text_area('Output Text Area', value=output_text, height=200)
# # Update output_text if the edited_text changes
# if edited_text != output_text:
#     output_text = edited_text

#########################################################################################
    


           





def page1():
    
    # Streamlit UI
    st.subheader('OpenAI Text Generation with Multiple Inputs')
        
    # Record audio from Microphone
    col1, col2 = st.columns(2)
    col1.button('Démarrer la reconnaissance :red_circle:', on_click=start_recognition, disabled=st.session_state.show_stop_button)
    col2.button('Arrêter la reconnaissance :white_square_button:', on_click=stop_recognition, disabled=st.session_state.show_start_button)

    if st.session_state.recognized_text:
        st.write("Texte reconnu :", st.session_state.recognized_text)
        process_and_synthesize_text(st.session_state.recognized_text)
        st.session_state.recognized_text = ""
    
    
     # File uploader for audio files
    uploaded_file = st.file_uploader('Choisir un fichier audio :vhs:', type=["wav", "mp3"])
    if uploaded_file is not None:
        file_extension = uploaded_file.name.split(".")[-1]
        if file_extension == "mp3":
            try:
                audio = AudioSegment.from_file(BytesIO(uploaded_file.read()), format="mp3")
                wav_path = "temp_audio_file.wav"
                audio.export(wav_path, format="wav")
            except Exception as e:
                print(f"Error converting file: {str(e)}")    
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
    
    
    # Text input area for user to enter text
    user_text_input = st.text_area("Enter your text here:", key="text_input")

    # File uploaders for documents
    uploaded_doc_file = st.file_uploader('Upload a document 📥', type=["txt", "docx", "pdf"])
    combined_input = handle_inputs(user_text_input, uploaded_doc_file)

    edit_combined_text_input = st.text_area("Text combined:", value=combined_input,key="combined_text_input",height=200)

    # Button to trigger text processing
    if st.button("Generate Resume"):
        
        if edit_combined_text_input:
            st.write("Combined Input:")
            st.write(edit_combined_text_input)

            # Process combined input with OpenAI
            processed_text = process_and_synthesize_text(edit_combined_text_input)

            st.write("OpenAI Response:")
            st.write(processed_text)
        else:
            st.warning("Please provide some input.")

def page2():
    
    # Streamlit UI
    st.subheader('Application de reconnaissance et de traitement vocal :studio_microphone:')

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
            try:
                audio = AudioSegment.from_file(BytesIO(uploaded_file.read()), format="mp3")
                wav_path = "temp_audio_file.wav"
                audio.export(wav_path, format="wav")
            except Exception as e:
                print(f"Error converting file: {str(e)}")    
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

    # File uploader for txt,pdf files
    uploaded_file = st.file_uploader("Choisir un fichier text", type=["txt", "docx", "pdf"])
    if uploaded_file is not None:
        
        # Read the content of the uploaded file
        file_extension = uploaded_file.name.split(".")[-1]

        if file_extension == "txt":
            text = uploaded_file.getvalue().decode("utf-8")
        elif file_extension == "docx":
            text = read_docx(uploaded_file)
        elif file_extension == "pdf":
            text = read_pdf(uploaded_file)
        
        st.write("Texte reconnu : {}".format(text))

        processed_text = process_text_with_gpt(text)
        st.write("Réponse GPT :", processed_text)
        synthesize_speech(processed_text)

    # Text input area for user to enter text
    user_input = st.text_area("Enter your text here:")

    # Button to trigger text processing
    if st.button("Generate Response"):
        if user_input:
            st.write("Input Text:")
            st.write(user_input)

            # Process text with OpenAI
            processed_text = process_text_with_gpt(user_input)
            synthesize_speech(processed_text)
        else:
            st.warning("Please enter some text.")
    
    
st.sidebar.title('Navigation')
selection = st.sidebar.radio("Go to", ['Multiple Inputs', 'Traitement vocal'])

if selection == 'Multiple Inputs':
    page1()
elif selection == 'Traitement vocal':
    page2()
