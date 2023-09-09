from lib.api import dynamodb


def get_config():
    config_data = dynamodb.get_item(Key={"id": "config"})

    return config_data["Item"]["data"]


config = get_config()


TOKEN = config["discord_token"]
SPOTIFY_REDIRECT_URL = config["spotify_redirect_url"]
MAX_MESSAGE_LENGTH = config["max_message_length"]
SLASH_GUILDS = config["slash_guilds"]
VIDEO_GRABBER_DOMAINS = config["video_grabber_domains"]
COG_EXTENSIONS = config["cog_extensions"]
