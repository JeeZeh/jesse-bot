import json

import pyrebase

config = {}

with open("firebase.json") as ffile:
    config = json.load(ffile)

firebase = pyrebase.initialize_app(config)
