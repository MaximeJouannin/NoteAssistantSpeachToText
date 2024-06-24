import openai 
import time

# API_KEY = os.getenv("AZURE_OPENAI_API_KEY") 
# RESOURCE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT") 
API_KEY= "45597a66237d464faebe8745618f5717"
RESOURCE_ENDPOINT ="https://inetum-open-ai-eastus.openai.azure.com/"
openai.api_type = "azure"
openai.api_key = API_KEY
openai.api_base = RESOURCE_ENDPOINT
openai.api_version = "2023-05-15"
#setx SPEECH_KEY your-key
#setx SPEECH_REGION your-region

SPEECH_KEY='03b704a152e04523aeb4e23f4bc0190f'
SPEECH_REGION='westeurope'

#pip install azure-cognitiveservices-speech


import os
import azure.cognitiveservices.speech as speechsdk

lang="en-US"
#lang="fr-FR"

def recognize_from_microphone(lang):
    # This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
    
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_config.speech_recognition_language=lang

    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    start =time.time()
    print(0)
    print("Speak into your microphone.")
    speech_recognition_result = speech_recognizer.recognize_once_async().get()
    
    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print("Recognized: {}".format(speech_recognition_result.text))
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
            print("Did you set the speech resource key and region values?")
    print(time.time()-start)
    #recognize word "computer" from inhouse pattern
    #listen to sentence

    #call chat gpt for an assessment of the best persona prompt
    #retrieve a system prompt
    #resubmit the sentence to chatgpt
    #vocalise the answer
    


    responsegpt = openai.ChatCompletion.create(
        engine="inetum-gpt-35-turbo-0613", # engine = "deployment_name".
        messages=[
        {"role": "system", "content": "You are an assistant and you always need to answer even if you don't know a correct answer. For every message you add to the message the equivalent sentiment carried by the message. You also suggest a matching bodily animation."},
        {"role": "user", "content": speech_recognition_result.text}        
        ]
    )

    
    #print(response['choices'][0]['message']['content'])
    text = responsegpt['choices'][0]['message']['content']
    print(text)
    print(time.time()-start)
    #text = speech_recognition_result.text

    # use the default speaker as audio output.
    #speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

    # Note: the voice setting will not overwrite the voice element in input SSML.
    speech_config.speech_synthesis_voice_name = 'en-US-JaneNeural'
    result = speech_synthesizer.speak_text_async(text).get()
    
    # Check result
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized for text [{}]".format(text))
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
    print(time.time()-start)
recognize_from_microphone(lang)