from unittest import TestCase

import cogs.notifications as notifcations
import cogs.text as text


class Tests(TestCase):
    def test_partition_message(self):
        too_long = f"{'hello world'*100}\n" * 3
        text.partition_message(too_long)
        assert len(text.partition_message(too_long)) == 2

    def test_censor_phrases(self):
        self.assertEqual(notifcations.Notifications.censor_phrase("hello", True), "||hello||")
        self.assertEqual(notifcations.Notifications.censor_phrase("hello", False), "h||ell||o")
        self.assertEqual(notifcations.Notifications.censor_phrase("one shot", False), "||one|| s||ho||t")
