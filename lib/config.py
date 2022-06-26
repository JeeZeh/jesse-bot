from lib.data import firebase

MAX_MESSAGE_LENGTH = 2000
COG_EXTENSIONS = ["text", "voice", "notifications", "external", "testing"]
SPOTIFY_REDIRECT_URL = firebase.database().child("config").child("spotify_redirect_url")
VIDEO_GRABBER_DOMAINS = ["tiktok.com"]

config = firebase.database().child("config").get().val()
