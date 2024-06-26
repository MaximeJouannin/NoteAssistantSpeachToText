import streamlit as st
import openai
import os
from io import StringIO
from PyPDF2 import PdfReader
from docx import Document

# Configuration de l'API OpenAI
API_KEY = "45597a66237d464faebe8745618f5717"
RESOURCE_ENDPOINT = "https://inetum-open-ai-eastus.openai.azure.com/"
openai.api_type = "azure"
openai.api_key = API_KEY
openai.api_base = RESOURCE_ENDPOINT
openai.api_version = "2023-05-15"

# Fonction pour traiter le texte avec GPT
def process_text_with_gpt(recognized_text):
    responsegpt = openai.ChatCompletion.create(
        engine="inetum-gpt-35-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant. Summarize the contatened provided text files and use bullet points when it's necessary."},
            {"role": "user", "content": recognized_text}
        ]
    )
    text = responsegpt['choices'][0]['message']['content']
    return text

# Fonction pour lire un fichier PDF
def read_pdf(file):
    pdf_reader = PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Fonction pour lire un fichier Word
def read_docx(file):
    doc = Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

# Fonction pour lire un fichier texte
def read_txt(file):
    content = file.read().decode("utf-8")
    return content

# Titre de l'application
st.title('Résumé de Réunion à partir de Fichiers Texte')

# Sélection des fichiers
uploaded_files = st.file_uploader("Choisissez des fichiers", type=["txt", "pdf", "docx"], accept_multiple_files=True)

if uploaded_files:
    combined_text = ""
    
    # Lecture et concaténation du contenu des fichiers
    for uploaded_file in uploaded_files:
        if uploaded_file.type == "text/plain":
            combined_text += read_txt(uploaded_file) + "\n"
        elif uploaded_file.type == "application/pdf":
            combined_text += read_pdf(uploaded_file) + "\n"
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            combined_text += read_docx(uploaded_file) + "\n"

    # Affichage du texte concaténé
    st.subheader('Texte Concaténé')
    st.text_area("Contenu", combined_text, height=300)

    # Traitement du texte avec GPT et affichage du résultat
    if st.button('Obtenir le Résumé'):
        with st.spinner('Traitement en cours...'):
            summary = process_text_with_gpt(combined_text)
        st.subheader('Résumé de la Réunion')
        st.write(summary)
