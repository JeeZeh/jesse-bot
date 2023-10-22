from lib.api import dynamodb


def get_config():
    config_data = dynamodb.get_item(Key={"id": "config"})

    return config_data["Item"]["data"]


config = get_config()

COMMAND_PREFIX = "!"
TOKEN: str = config["discord_token"]
SPOTIFY_REDIRECT_URL: str = config["spotify_redirect_url"]
MAX_MESSAGE_LENGTH: int = config["max_message_length"]
SLASH_GUILDS: list[int] = config["slash_guilds"]
DISABLE_SECRETS_FOR_GUILDS: list[int] = config["disable_secrets_for_guilds"]
VIDEO_GRABBER_DOMAINS: list[str] = config["video_grabber_domains"]
SONG_TRANSLATE_DOMAINS: list[str] = config["song_translate_domains"]
COG_EXTENSIONS: list[str] = config["cog_extensions"]
