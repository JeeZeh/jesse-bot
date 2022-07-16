import json
from typing import Any

import pyrebase
from googleapiclient.discovery import build
from spotipy import Spotify, SpotifyClientCredentials

firebase: Any = None
spotify: Any = None
youtube: Any = None

with open("firebase.json") as fp:
    firebase = pyrebase.initialize_app(json.load(fp))


with open("spotify.json") as fp:
    creds = json.load(fp)
    spotify = Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
        )
    )

with open("youtube.json") as fp:
    creds = json.load(fp)
    api_service_name = "youtube"
    api_version = "v3"
    # Get credentials and create an API client
    youtube = build(api_service_name, api_version, developerKey=creds["api_key"])
