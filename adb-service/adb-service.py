#!/usr/bin/env python

#python 2.7.x

import subprocess32
from flask import Flask, request, Response, abort
from flask_restful import Resource, Api
from json import dumps
from flask_jsonpify import jsonify
import yaml
import sys
import re
import time
import calendar
import threading
import Queue
import pprint
from flask_httpauth import HTTPBasicAuth
from flask_restful import reqparse
import os
from random import randint
import logging
from ipaddress import ip_network, ip_address
import json
import requests

USE_THREADING = False
CONN_STATUS = False
LAST_RECONNECT = 0

with open("config.yaml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

with open("config-secure.yaml", 'r') as ymlfile:
    cfg_secure = yaml.load(ymlfile)

with open("trusted-ips.yaml", 'r') as ymlfile:
    cfg['trusted_ips'] = yaml.load(ymlfile)

cfg['connection'] = cfg_secure['connection']
cfg['credentials'] = cfg_secure['credentials']

pp = pprint.PrettyPrinter(indent=4)
pp.pprint(cfg)

#sys.exit()



def thread_worker():
    print ("Starting worker")
    global CONN_STATUS
    CONN_STATUS = False
    while True:
        data = q.get()
        if data is None:
            break
        print "picked from queue: " + data
        run_adb(data)
        q.task_done()

    print ("Exiting worker")

def run_cmd(command):
    print "run_cmd: " + command
    try:
        output = subprocess32.check_output(command.split(" "), stderr=subprocess32.STDOUT, timeout=10)
    except OSError as ose:
        print "Exception running command: " + str(ose)
        return False
    except subprocess32.CalledProcessError as cpe:
        print "CalledProcessError exception: " + str(cpe)
        time.sleep(3)
        print "Trying again..."
        try:
            output = subprocess32.check_output(command.split(" "), stderr=subprocess32.STDOUT, timeout=10)
        except OSError as ose:
            print "Exception running command: " + str(ose)
            return False
        except subprocess32.CalledProcessError as cpe:
            print "CalledProcessError exception: " + str(cpe)
            print "Giving up!"
            return False

    print "run_cmd output: " + output
    return output

def reconnect():
    global CONN_STATUS
    global LAST_RECONNECT

    # check if we last reconnected more than 10 mins ago, if so then force a reconnect anyway
    # this combats the fact that adb will sometimes return "already connected" when trying
    # to connect, even if the connection is actually dead, which then means subsequent
    # attempts to run a command will return an error
    time_now = calendar.timegm(time.gmtime())
    if (time_now - LAST_RECONNECT) > (60 * 10):
        print "forcing reconnect as we haven't reconnected since %d and it is now %d" % (LAST_RECONNECT, time_now)
        out = run_cmd("sudo /usr/bin/adb kill-server ; sudo /usr/bin/adb start-server")
        if out == False:
            CONN_STATUS = False
            return False

    out = run_cmd("sudo /usr/bin/adb connect %s" % (cfg['connection']['ip']))
    if out == False:
        CONN_STATUS = False
        return False
    regex = re.compile(r'unable to connect', re.MULTILINE)
    if regex.search(out):
        CONN_STATUS = False
    else:
        CONN_STATUS = True
        print "reconnect is setting CONN_STATUS to True"
        LAST_RECONNECT = time_now
    return CONN_STATUS

def run_adb(command):
    global CONN_STATUS
    print "enter run_adb CONN_STATUS = " + str(CONN_STATUS)

    if CONN_STATUS == False:
        reconnect()
        print "after reconnect() CONN_STATUS = " + str(CONN_STATUS)
        if CONN_STATUS == False:
            return False


    result = run_cmd("sudo /usr/bin/adb " + command)
    if result == False:
        return False
    else:
        # TODO: pass message back to caller to use in response in case of error
        return True

def queue_adb(command):
    global USE_THREADING
    if USE_THREADING == True:
        print "putting on queue: " + command
        q.put(command)
        return True
    else:
        return run_adb(command)

def button_press(button):

    if button in cfg['buttons'].keys():
        keycode = cfg['buttons'][button]
    else:
        return False, 404, "button not found"

    result = reconnect()
    if result == False:
        return False, 500, "adb could not connect"

    result = queue_adb("shell input keyevent " + keycode)
    if result == False:
        return False, 500, "error running adb command"

    return True, 200, "success"

def run_action_sequence(action_name, args):

    if action_name == 'check_programme':
        if 'name' in args.keys():
            if args['name'] in cfg['programmes'].keys():
                return True, 200, "programme exists"
            else:
                return False, 404, "could not find programme"
        else:
            return False, 500, "programme name not specified in 'name' parameter"

    result = reconnect()
    if result == False:
        return False, 500, "adb could not connect"

    if action_name == 'play_programme':
        if 'name' in args.keys():
            if args['name'] in cfg['programmes'].keys():
                sequence = cfg['programmes'][args['name']]
            else:
                return False, 404, "could not find programme"
        else:
            return False, 500, "programme name not specified in 'name' parameter"
    elif action_name in cfg['actions'].keys():
        sequence = cfg['actions'][action_name]
    else:
        return False, 404, "action name not found"


    times = 1
    if action_name == 'volume_up' or action_name == 'volume_down' or action_name == 'volume_set':
        if 'amount' in args.keys():
            times = int(args['amount'])

    for action in sequence:
        print "running action: " + str(action)
        if 'wait' in action.keys():
            time.sleep(int(action['wait']))
        elif 'keypress' in action.keys():
            if times > 1:
                keycodes = (action['keypress'] + " ") * times
                if action_name == 'volume_set':
                    result = queue_adb("shell input keyevent --longpress " + ('KEYCODE_VOLUME_DOWN ' * 40))
                result = queue_adb("shell input keyevent --longpress " + keycodes)
            else:
                result = queue_adb("shell input keyevent " + action['keypress'])

        elif 'keypress_multiple' in action.keys():
            keycodes = (action['keypress_multiple'] + " ") * int(action['times'])
            result = queue_adb("shell input keyevent --longpress " + keycodes)

        elif 'keypress_rand' in action.keys():
            rand_times = (randint(int(action['min_times']), int(action['max_times'])))
            if rand_times > 0:
                keycodes = (action['keypress_rand'] + " ") * rand_times
                result = queue_adb("shell input keyevent --longpress " + keycodes)

        elif 'delete' in action.keys():
            keycodes = "KEYCODE_DEL " * int(action['delete'])
            result = queue_adb("shell input keyevent --longpress " + keycodes)

        elif 'text' in action.keys():
            param = action[action.keys()[0]]
            if param[0] == '<' and param[-1] == '>':
                arg = param[1:-1]
                if arg in args.keys():
                    param = args[arg]
                else:
                    return False, 500, "query parameter '" + arg + "' needs to be specified for this action"

            result = queue_adb("shell input text \"" + param + "\"")

        elif 'app' in action.keys():
            result = queue_adb("shell am start " + cfg['apps'][action['app']] + "/" + cfg['activities'][action['activity']])

        elif 'raw' in action.keys():
            result = queue_adb(action['raw'])

        if result == False:
            return False, 500, "error running adb command"

    return True, 200, "success"

def check_aws_ip(ipaddr):
    print "check_aws_ip: checking if " + ipaddr + " is in eu-west-1"
    response = requests.get('https://ip-ranges.amazonaws.com/ip-ranges.json')

    ip_json = json.loads(response.text)
    prefixes = ip_json['prefixes']
    my_ip = ip_address(unicode(ipaddr))
    region = 'Unknown'
    for prefix in prefixes:
        if my_ip in ip_network(prefix['ip_prefix']):
            region = prefix['region']
            break
    if region == 'eu-west-1':
        print "check_aws_ip: adding " + ipaddr + " to list of trusted ips"
        cfg['trusted_ips'] += [ipaddr]
        with open("trusted-ips.yaml", 'w') as ymlfile:
            yaml.dump(cfg['trusted_ips'], ymlfile, default_flow_style=False)
        return True
    else:
        print "check_aws_ip: " + ipaddr + " doesnt seem to be in eu-west-1 therefore rejecting"
        return False


class localFlask(Flask):
        def process_response(self, response):
            #Every response will be processed here first
            response.headers['server'] = 'TomServer/1.0.0'
            return(response)

# set up logging

out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
out_hdlr.setLevel(logging.INFO)
# append to the global logger.
logging.getLogger().addHandler(out_hdlr)
logging.getLogger().setLevel(logging.INFO)


app = localFlask(__name__)
#app = Flask(__name__)
app.config['TESTING'] = False
app.config['ENV'] = 'production'
app.config['DEBUG'] = False

app.logger.handlers = []
app.logger.propagate = True

api = Api(app)
auth = HTTPBasicAuth()

@auth.verify_password
def verify(username, password):
    if not (username and password):
        return False
    return cfg['credentials'].get(username) == password

@app.before_request
def limit_remote_addr():
    #if request.remote_addr != '10.20.30.40':
    #    abort(403)  # Forbidden
    #print "request is from " + str(request.remote_addr)
    # stop any requests from anywhere other than local network or aws lambda function
    if str(request.remote_addr)[0:7] != "192.168" and str(request.remote_addr) not in cfg['trusted_ips']:
        result = check_aws_ip(str(request.remote_addr))
        if result == False:
            print "request is not from an IP address we trust"
            return '', 403

# tell the service to refresh the connection to the TV
class Connect(Resource):
    @auth.login_required
    def get(self):
        print "connect: about to reconnect, CONN_STATUS is " + str(CONN_STATUS)
        result = reconnect()
        print "connect: CONN_STATUS is now " + str(CONN_STATUS)

        if result == False:
            return {'success': str(result), 'message': 'adb could not connect'}, 500
        else:
            return {'success': str(result), 'message': 'connected'}, 200


# tell the service to run an action from the config file
class Action(Resource):
    @auth.login_required
    def get(self, action_name):

        parser = reqparse.RequestParser()
        parser.add_argument('query', type=str)
        parser.add_argument('amount', type=int)
        parser.add_argument('name', type=str)
        args = parser.parse_args()

        print "action name:'" + action_name + "' args:" + str(args)

        result, status_code, message = run_action_sequence(action_name, args)
        return {'success': str(result), 'message': message}, status_code

# tell the service to run a raw adb command
class Raw(Resource):
    @auth.login_required
    def get(self, command):
        print "raw command:'" + command
        #reconnect()
        #result = queue_adb(command)
        result = False
        if result == False:
            return {'success': str(result), 'message': 'error running adb command'}, 500
        else:
            return {'success': str(result), 'message': 'success'}, 200

class Button(Resource):
    @auth.login_required
    def get(self, button):
        print "button:" + button

        result, status_code, message = button_press(button)
        return {'success': str(result), 'message': message}, status_code

api.add_resource(Connect, '/connect') # Route_1
api.add_resource(Action, '/action/<action_name>') # Route_1
api.add_resource(Raw, '/raw/<command>') # Route_1
api.add_resource(Button, '/button/<button>') # Route_1



if USE_THREADING == True:
    q = Queue.Queue()
    threads = []
    t = threading.Thread(target=thread_worker)
    t.start()
    threads.append(t)

if __name__ == '__main__':
     app.run(host='192.168.1.30', port=6707) #, debug=True)
