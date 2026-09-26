import json
import base64
import datetime
import tempfile
import unittest
from unittest.mock import patch
from formbricks_jev import classify
from standardwebhooks.webhooks import Webhook

class WebhookTest(unittest.TestCase):
    def test_idempotent_feedback(self):
        class Client:
            calls = 0
            def decide(self, text):
                self.calls += 1
                assert text == 'useful'
                return {'route':'yes','probability':0.9,'state_sha256':'abc'}
        client = Client()
        body = json.dumps({'type':'feedback_record.created','data':{'value_text':'useful'}}).encode()
        with tempfile.TemporaryDirectory() as directory, patch('formbricks_jev.Webhook') as webhook:
            path = directory + '/decisions.db'
            first = classify(body, {'webhook-id':'evt_1'},secret='whsec_dummy',db_path=path,question='Useful?',client=client)
            second = classify(body, {'webhook-id':'evt_1'},secret='whsec_dummy',db_path=path,question='Useful?',client=client)
            self.assertEqual('stored', first['status'])
            self.assertEqual('duplicate', second['status'])
            self.assertEqual(1, client.calls)
            self.assertEqual(2, webhook.return_value.verify.call_count)

    def test_real_signature_and_rejection(self):
        secret = 'whsec_' + base64.b64encode(b'01234567890123456789012345678901').decode()
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        body = json.dumps({'type':'feedback_record.created','data':{'value_text':'useful'}}).encode()
        headers = {'webhook-id':'evt_signed', 'webhook-timestamp':str(int(timestamp.timestamp())),
                   'webhook-signature':Webhook(secret).sign('evt_signed',timestamp,body.decode())}
        class Client:
            def decide(self, text):
                return {'route':'yes','probability':0.9,'state_sha256':'abc'}
        with tempfile.TemporaryDirectory() as directory:
            result = classify(body,headers,secret=secret,db_path=directory+'/decisions.db',question='Useful?',client=Client())
            self.assertEqual('stored',result['status'])
            with self.assertRaises(Exception):
                classify(body+b' ',headers,secret=secret,db_path=directory+'/decisions.db',question='Useful?',client=Client())
