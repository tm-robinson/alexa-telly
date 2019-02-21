# alexa-telly

This repository contains:

* An alexa skill interaction model that allows a user to ask alexa to
perform various actions on their android TV.
* A lambda function that the alexa skill can call to respond to requests, which
calls a REST API to fire adb commands to an android TV.
* A flask based REST API server that can be called by the lambda function to
process commands and translate them into adb command lines that control
an android TV.

Requirements:

* Android TV that is running in developer mode and can be connected to via adb.
* Local linux or MacOS machine that can host the REST API server and has
adb installed.
* Amazon Echo or another device that supports Alexa.
* AWS account where the Lambda function can be created and hosted.
* Alexa developer account where the Alexa skill can be created.

How to set up:

More detail on steps 6-15 can be found here: https://tutorials.botsfloor.com/how-to-build-a-hello-world-alexa-skill-bcea0d01ee8f

1. Put your Android TV into developer mode by going into settings and pressing
enter on the version number several times.
2. Install adb onto your local server and test you can connect to the TV and
issue some adb commands to it (e.g. `adb connect 192.168.1.123`
followed by `adb shell input keyevent KEYCODE_VOLUME_UP` )
3. Download the repository locally and edit the config-secure.yaml files to
set a username and password for authentication between the lambda function
and adb service REST API server.
4. Edit the adb_service.py file to set the IP address of your server to bind
to (near end of file).
5. Add adb to /etc/sudoers so that the REST API server can call it whilst
running as another user.
5. Run adb_service.py and test you can call it and get responses and that
it can control the TV (e.g. run
`curl -v -u alexa:Password1 http://192.168.1.10:6707/action/` ) where
the IP address is the IP of your local Linux or MacOS server
6. Go to the Alexa developer console and create a new skill, and paste in
the latest `interaction-model-vX.json` into the JSON editor.  Give your skill
an invocation name e.g. `telly remote`.
7. Set up a dynamic DNS service and set up port forwarding on your
router so your REST API server can be connected to from AWS.  Set the
rest-endpoint in the lamba function's config-secure.yaml to point to it.
8. Go to the AWS console and create a lambda function.
9. Zip up the lambda function directory by running
`zip -r9 ../function.zip .` from within the lambda-function directory.
10. Upload the resultant zip file to the Lambda function on the AWS console.
11. Set the lambda function timeout to 1 minute.
12. On the alexa developer console, point the skill to the lambda function.
13. Ensure the skill's language is set to the same language as your Echo devices.
14. Save and build the interaction model.
15. On the testing tab, ensure testing is enabled in Development.
16. Test the skill in the simulator by typing `alexa open telly remote`
and then `switch off`.

Other repositories with examples that were helpful in creating this:
https://github.com/DarrenVictoriano/daaf/blob/master/tools/ADB_Action_Scipt.py
