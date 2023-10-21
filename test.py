import cogs.text as text
from cogs.notifications import Notifications
from lib.passive import try_match_youtube_video_for_spotify_track


class Tests:
    # bot = load_bot(bot)

    def test_partition_message(self):
        too_long = f"{'hello world'*100}\n" * 3
        text.partition_message(too_long)
        assert len(text.partition_message(too_long)) == 2

    def test_censor_phrases(self):
        assert Notifications.censor_phrase("hello", True) == "||hello||"
        assert Notifications.censor_phrase("hello", False) == "h||ell||o"
        assert Notifications.censor_phrase("one shot", False) == "||one|| s||ho||t"

    def test_spotify_grab_info(self):
        assert (
            try_match_youtube_video_for_spotify_track(
                "https://open.spotify.com/track/04mhI65E8cdqrhq6mh5IrJ?si=75d1be99334047ef"
            )
            is not None
        )

    # @pytest.mark.asyncio
    # async def test_permissions(self):
    #     notifications_: Notifications = self.bot.get_cog("notifications")
    #     assert notifications_ is not None

    #     test_user_bad = "113107906815094784"
    #     test_user_good = "359409912893276161"
    #     test_channel = "946167332303147049"

    #     voice_channel = self.bot.get_channel(test_channel)
    #     user_good = self.bot.get_user(test_user_good)
    #     user_bad = self.bot.get_user(test_user_bad)

    #     assert notifications_.user_can_connect_to_channel(user_good, voice_channel)
    #     assert not notifications_.user_can_connect_to_channel(user_bad, voice_channel)
