import unittest
from jev_common import JevClient


class JevClientTest(unittest.TestCase):
    def test_yes_no_uncertainty_and_budget(self):
        scores = iter([0.9, 0.1, 0.5])
        client = JevClient("Is this relevant?", max_calls=3,
            transport=lambda payload: {"answers": {"decision": {"type": "noul", "noul": next(scores)}}})
        self.assertEqual("yes", client.decide("first")["route"])
        self.assertEqual("no", client.decide("second")["route"])
        self.assertEqual("review", client.decide("third")["route"])
        self.assertEqual("review", client.decide("fourth")["route"])

    def test_invalid_answer_fails_closed(self):
        client = JevClient("Is this relevant?", transport=lambda payload: {"answers": {"decision": {"type": "noul", "noul": "yes"}}})
        self.assertEqual("failure", client.decide("data")["route"])

    def test_empty_and_oversized_never_call_remote(self):
        client = JevClient("Is this relevant?", max_bytes=3, transport=lambda payload: self.fail("called"))
        self.assertEqual("review", client.decide("")["route"])
        self.assertEqual("review", client.decide("long")["route"])


if __name__ == "__main__":
    unittest.main()
