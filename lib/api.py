import json
from typing import Any

import pyrebase
from googleapiclient.discovery import build
from spotipy import Spotify, SpotifyClientCredentials
from .logger import logger


firebase: Any = None
spotify: Any = None
youtube: Any = None


def init():
    with open("service_credentials.json") as fp:
        creds = json.load(fp)
        init_spotify(creds["spotify"])
        init_firebase(creds["firebase"])
        init_youtube(creds["youtube"])


def init_youtube(creds):
    global youtube
    logger.info("Initializing YouTube API")
    api_service_name = "youtube"
    api_version = "v3"
    # Get credentials and create an API client
    youtube = build(api_service_name, api_version, developerKey=creds["api_key"])


def init_firebase(creds):
    global firebase
    logger.info("Initializing Firebase API")
    firebase = pyrebase.initialize_app(creds)


def init_spotify(creds):
    global spotify
    logger.info("Initializing Spotify API")
    spotify = Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
        )
    )


init()
