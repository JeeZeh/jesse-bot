from unittest import TestCase

import cogs.notifications as notifications
import cogs.text as text
from cogs.passive import try_match_youtube_video_for_spotify_track


class Tests(TestCase):
    def test_partition_message(self):
        too_long = f"{'hello world'*100}\n" * 3
        text.partition_message(too_long)
        assert len(text.partition_message(too_long)) == 2

    def test_censor_phrases(self):
        self.assertEqual(notifications.Notifications.censor_phrase("hello", True), "||hello||")
        self.assertEqual(notifications.Notifications.censor_phrase("hello", False), "h||ell||o")
        self.assertEqual(notifications.Notifications.censor_phrase("one shot", False), "||one|| s||ho||t")

    def test_spotify_grab_info(self):
        self.assertIsNotNone(
            try_match_youtube_video_for_spotify_track(
                "https://open.spotify.com/track/04mhI65E8cdqrhq6mh5IrJ?si=75d1be99334047ef"
            )
        )
