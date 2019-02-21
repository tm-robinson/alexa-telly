

from __future__ import print_function
import requests
from requests.auth import HTTPBasicAuth
import yaml
import json
import re

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }

def build_progressive_response(request_id, speech):
    return {
        "header": {
            "requestId": request_id
        },
        "directive": {
            "type": "VoicePlayer.Speak",
            "speech": speech
        }
    }

def send_progressive_response(request_id, api_endpoint, api_access_token, speech):
    response = build_progressive_response(request_id, speech)

    url = api_endpoint + '/v1/directives'

    print("sending progressive response: " + str(response))
    header = {'Authorization': 'Bearer ' + api_access_token}
    try:
        response = requests.post(url, json=response, headers=header, timeout=5)
    except Exception as e:
        print("exception during post request: " + str(e))
        return False

    print("result: " + str(response))
    return True

def call_adb_service(function, config, param=None, timeout=5):
    rest_url = config['rest-endpoint'] + function
    print("call adb service: url '" + rest_url + "' params: "+ str(param))
    try:
        response = requests.get(rest_url, params=param, timeout=timeout, auth=HTTPBasicAuth(config['user'],config['pass']))
    except Exception as e:
        print("exception during adb service get request: " + str(e))
        return False, "connection issue", 0

    if response.status_code != 200:
        if response.status_code == 403:
            return False, 'permission denied', response.status_code
        data = json.loads(response.text)
        return False, data['message'], response.status_code
    else:
        return True, "", response.status_code


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Welcome to Tom's TV remote control.  I can skip ads, search on " \
                    "youtube, netflix or amazon, play specific programmes, " \
                    "set the volume, or switch the telly off."

    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "What would you like me to do on the telly?"
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def get_fallback_response():

    session_attributes = {}
    card_title = "Error"
    speech_output = "Sorry I'm not sure what you mean, please try again."

    reprompt_text = "What would you like me to do on the telly?"
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you, goodbye! "
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def skip_ad(intent, session, request_id, api_endpoint, api_access_token, config):
    session_attributes = {}
    reprompt_text = None
    should_end_session = True

    result = send_progressive_response(request_id, api_endpoint, api_access_token, "Ok, skipping ad.")
    if result == False:
        speech_output = "There was an error."
    else:
        # call synchronous rest service - will return 200 if successful and 500 if failure
        rest_function = config['rest-functions']['action']['name'] + '/' + config['rest-actions']['skip_ad']['name']
        result, message, code = call_adb_service(rest_function, config)
        if result == False:
            speech_output = "There was an error.  It was " + message + "."
        else:
            speech_output = "Ad skipped."

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def switch_off(intent, session, request_id, api_endpoint, api_access_token, config):
    session_attributes = {}
    reprompt_text = None
    should_end_session = True

    result = send_progressive_response(request_id, api_endpoint, api_access_token, "Ok, switching off.")
    if result == False:
        speech_output = "There was an error."
    else:
        # call synchronous rest service - will return 200 if successful and 500 if failure
        rest_function = config['rest-functions']['action']['name'] + '/' + config['rest-actions']['switch_off']['name']
        result, message, code = call_adb_service(rest_function, config)
        if result == False:
            speech_output = "There was an error.  It was " + message + "."
        else:
            speech_output = "Telly switched off."

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def button(intent, session, request_id, api_endpoint, api_access_token, config):
    session_attributes = {}
    reprompt_text = None
    if 'Button' in intent['slots'] and 'value' in intent['slots']['Button'].keys():
        should_end_session = True
        button_name = intent['slots']['Button']['value']
        if button_name in config['rest-functions']['button']['buttons']:
            result = send_progressive_response(request_id, api_endpoint, api_access_token, "Ok.")
            if result == False:
                speech_output = "There was an error."
            else:
                # call synchronous rest service - will return 200 if successful and 500 if failure
                rest_function = config['rest-functions']['button']['name'] + '/' + button_name
                result, message, code = call_adb_service(rest_function, config)
                if result == False:
                    speech_output = "There was an error.  It was " + message + "."
                else:
                    speech_output = "Done."
        else:
            result = send_progressive_response(request_id, api_endpoint, api_access_token, "Sorry I don't know how to press the " + button_name + " button.")
            if result == False:
                speech_output = "There was an error."
    else:
        speech_output = "I'm not sure what button you want me to press, please try again."
        should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))


def youtube_search(intent, session, request_id, api_endpoint, api_access_token, config):
    session_attributes = {}
    reprompt_text = None
    if 'SearchTerm' in intent['slots'] and 'value' in intent['slots']['SearchTerm'].keys():
        should_end_session = True
        search_term = intent['slots']['SearchTerm']['value']
        result = send_progressive_response(request_id, api_endpoint, api_access_token, "Ok, searching youtube for " + search_term + ".")
        if result == False:
            speech_output = "There was an error."
        else:
            # call synchronous rest service - will return 200 if successful and 500 if failure
            rest_function = config['rest-functions']['action']['name'] + '/' + config['rest-actions']['youtube_search']['name']
            result, message, code = call_adb_service(rest_function, config, param={'query': search_term}, timeout=40)
            if result == False:
                speech_output = "There was an error.  It was " + message + "."
            else:
                speech_output = "Ok, I've finished."

    else:
        speech_output = "I'm not sure what you want me to search for, please try again."
        should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def netflix_search(intent, session, request_id, api_endpoint, api_access_token, config):
    session_attributes = {}
    reprompt_text = None
    if 'SearchTerm' in intent['slots'] and 'value' in intent['slots']['SearchTerm'].keys():
        should_end_session = True
        search_term = intent['slots']['SearchTerm']['value']
        result = send_progressive_response(request_id, api_endpoint, api_access_token, "Ok, searching netflix for " + search_term + ".")
        if result == False:
            speech_output = "There was an error."
        else:
            # call synchronous rest service - will return 200 if successful and 500 if failure
            rest_function = config['rest-functions']['action']['name'] + '/' + config['rest-actions']['netflix_search']['name']
            result, message, code = call_adb_service(rest_function, config, param={'query': search_term}, timeout=45)
            if result == False:
                speech_output = "There was an error.  It was " + message + "."
            else:
                speech_output = "Ok, I've finished."

    else:
        speech_output = "I'm not sure what you want me to search for, please try again."
        should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))


def amazon_search(intent, session, request_id, api_endpoint, api_access_token, config):
    session_attributes = {}
    reprompt_text = None
    if 'SearchTerm' in intent['slots'] and 'value' in intent['slots']['SearchTerm'].keys():
        should_end_session = True
        search_term = intent['slots']['SearchTerm']['value']
        result = send_progressive_response(request_id, api_endpoint, api_access_token, "Ok, searching amazon for " + search_term + ".")
        if result == False:
            speech_output = "There was an error."
        else:
            # call synchronous rest service - will return 200 if successful and 500 if failure
            rest_function = config['rest-functions']['action']['name'] + '/' + config['rest-actions']['amazon_search']['name']
            result, message, code = call_adb_service(rest_function, config, param={'query': search_term}, timeout=40)
            if result == False:
                speech_output = "There was an error.  It was " + message + "."
            else:
                speech_output = "Ok, I've finished."

    else:
        speech_output = "I'm not sure what you want me to search for, please try again."
        should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def play_programme(intent, session, request_id, api_endpoint, api_access_token, config):
    session_attributes = {}
    reprompt_text = None
    if 'Programme' in intent['slots'] and 'value' in intent['slots']['Programme'].keys():
        should_end_session = True
        programme = (intent['slots']['Programme']['value']).lower()
        regex = re.compile('[^a-zA-Z ]')
        programme = regex.sub('', programme)
        # call the rest API to see if the requested programme is one of the ones we know how to play?  If not, respond with
        result = send_progressive_response(request_id, api_endpoint, api_access_token, "Ok.")
        if result == False:
            speech_output = "There was an error."
        else:
            rest_function = config['rest-functions']['action']['name'] + '/' + config['rest-actions']['check_programme']['name']
            result, message, code = call_adb_service(rest_function, config, param={'name': programme})
            if result == False:
                if code == 404:
                    speech_output = "Sorry, that's not a programme I know about, please ask Tom to add it to the list."
                else:
                    speech_output = "There was an error.  It was " + message + "."
            else:
                result = send_progressive_response(request_id, api_endpoint, api_access_token, "Playing " + programme + ".")
                if result == False:
                    speech_output = "There was an error."
                else:
                    rest_function = config['rest-functions']['action']['name'] + '/' + config['rest-actions']['play_programme']['name']
                    result, message, code = call_adb_service(rest_function, config, param={'name': programme}, timeout=45)
                    if result == False:
                        speech_output = "There was an error.  It was " + message + "."
                    else:
                        speech_output = "It's playing."

    else:
        speech_output = "I'm not sure what you want me to play, please try again."
        should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def adjust_volume(intent, session, request_id, api_endpoint, api_access_token, config):
    session_attributes = {}
    reprompt_text = None
    should_end_session = True
    if intent['name'] == 'VolumeSetIntent':
        direction = "set"
    elif intent['name'] == 'VolumeUpIntent':
        direction = "up"
    else:
        direction = "down"

    if 'Amount' in intent['slots'] and 'value' in intent['slots']['Amount'].keys():
        amount = int(intent['slots']['Amount']['value'])
    else:
        if direction == "set":
            amount = 10
        else:
            amount = 3

    if direction == "set":
        speech_output = "Setting volume to " + str(amount) + "."
    else:
        speech_output = "Turning volume " + direction + " by " + str(amount) + "."

    result = send_progressive_response(request_id, api_endpoint, api_access_token, speech_output)
    if result == False:
        speech_output = "There was an error."
    else:
        rest_function = config['rest-functions']['action']['name'] + '/' + config['rest-actions']['volume_' + direction]['name']
        result, message, code = call_adb_service(rest_function, config, param={'amount': str(amount)}, timeout=10)
        if result == False:
            speech_output = "There was an error."
        else:
            speech_output = "Volume adjusted."

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session, context, config):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    print("intent_request: " + str(intent_request))
    print("session: " + str(session))

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']
    request_id = intent_request['requestId']
    api_endpoint = context['System']['apiEndpoint']
    api_access_token = context['System']['apiAccessToken']

    # Dispatch to your skill's intent handlers
    if intent_name == "SkipAdIntent":
        return skip_ad(intent, session, request_id, api_endpoint, api_access_token, config)
    elif intent_name == "SwitchOffIntent":
        return switch_off(intent, session, request_id, api_endpoint, api_access_token, config)
    elif intent_name == "ButtonIntent":
        return button(intent, session, request_id, api_endpoint, api_access_token, config)
    elif intent_name == "YoutubeSearchIntent":
        return youtube_search(intent, session, request_id, api_endpoint, api_access_token, config)
    elif intent_name == "NetflixSearchIntent":
        return netflix_search(intent, session, request_id, api_endpoint, api_access_token, config)
    elif intent_name == "AmazonSearchIntent":
        return amazon_search(intent, session, request_id, api_endpoint, api_access_token, config)
    elif intent_name == "ProgrammeIntent":
        return play_programme(intent, session, request_id, api_endpoint, api_access_token, config)
    elif intent_name == "VolumeUpIntent" or intent_name == "VolumeDownIntent" or intent_name == "VolumeSetIntent":
        return adjust_volume(intent, session, request_id, api_endpoint, api_access_token, config)
    elif intent_name == "AMAZON.FallbackIntent":
        return get_fallback_response()
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    with open("config.yaml", 'r') as ymlfile:
        config = yaml.load(ymlfile)

    with open("config-secure.yaml", 'r') as ymlfile:
        config_secure = yaml.load(ymlfile)

    config['user'] = list(config_secure['rest-credentials'].keys())[0]
    config['pass'] = config_secure['rest-credentials'][config['user']]
    config['rest-endpoint'] = config_secure['rest-endpoint']

    print(config)



    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'], event['context'], config)
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
