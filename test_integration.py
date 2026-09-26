import json
import base64
import datetime
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from formbricks_jev import Handler, classify
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

    def test_concurrent_retry_does_not_call_jev_twice(self):
        started, release = threading.Event(), threading.Event()
        class Client:
            calls = 0
            def decide(self, text):
                self.calls += 1
                started.set()
                release.wait(2)
                return {'route':'yes','probability':0.9,'state_sha256':'abc'}
        client = Client()
        body = json.dumps({'type':'feedback_record.created','data':{'value_text':'useful'}}).encode()
        with tempfile.TemporaryDirectory() as directory, patch('formbricks_jev.Webhook'):
            path = directory + '/decisions.db'
            worker = threading.Thread(target=lambda: classify(body,{'webhook-id':'same'},secret='test',db_path=path,question='Useful?',client=client))
            worker.start()
            self.assertTrue(started.wait(2))
            with self.assertRaises(RuntimeError):
                classify(body,{'webhook-id':'same'},secret='test',db_path=path,question='Useful?',client=client)
            release.set()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertEqual(1, client.calls)
            self.assertEqual('duplicate', classify(body,{'webhook-id':'same'},secret='test',db_path=path,question='Useful?',client=client)['status'])

    def test_admin_read_requires_token(self):
        with tempfile.TemporaryDirectory() as directory:
            path = directory + '/decisions.db'
            with patch('formbricks_jev.Webhook'):
                class Client:
                    def decide(self, text):
                        return {'route':'yes','probability':0.9,'state_sha256':'abc'}
                body = json.dumps({'type':'feedback_record.created','data':{'value_text':'useful'}}).encode()
                classify(body,{'webhook-id':'evt_admin'},secret='test',db_path=path,question='Useful?',client=Client())
            with patch.dict(os.environ, {'JEV_DB_PATH':path,'FORMBRICKS_JEV_ADMIN_TOKEN':'admin-test'}):
                server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
                thread = threading.Thread(target=server.serve_forever,daemon=True)
                thread.start()
                url = f'http://127.0.0.1:{server.server_port}/decisions?event_id=evt_admin'
                try:
                    with self.assertRaises(urllib.error.HTTPError) as denied:
                        urllib.request.urlopen(url, timeout=2)
                    self.assertEqual(401,denied.exception.code)
                    request = urllib.request.Request(url,headers={'Authorization':'Bearer admin-test'})
                    with urllib.request.urlopen(request,timeout=2) as response:
                        self.assertEqual('yes',json.load(response)['route'])
                finally:
                    server.shutdown()
                    server.server_close()
