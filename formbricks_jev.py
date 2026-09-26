"""Signed Formbricks Hub webhook receiver with idempotent SQLite decisions."""
import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from standardwebhooks.webhooks import Webhook
from jev_common import JevClient

def connect(path):
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE IF NOT EXISTS decisions (event_id TEXT PRIMARY KEY, route TEXT NOT NULL, probability REAL, state_sha256 TEXT)')
    return db

def classify(body, headers, *, secret, db_path, question, client=None):
    Webhook(secret).verify(body, headers)
    event_id = headers.get('webhook-id') or headers.get('Webhook-Id')
    if not event_id or len(event_id) > 200:
        raise ValueError('Missing webhook ID')
    event = json.loads(body)
    if event.get('type') not in ('feedback_record.created', 'feedback_record.updated'):
        return {'status':'ignored'}
    data = event.get('data')
    if not isinstance(data, dict):
        raise ValueError('Expected feedback record object')
    with connect(db_path) as db:
        existing = db.execute('SELECT route,probability,state_sha256 FROM decisions WHERE event_id=?', (event_id,)).fetchone()
        if existing:
            return {'status':'duplicate','route':existing[0],'probability':existing[1],'state_sha256':existing[2]}
        judge = client or JevClient(question)
        result = judge.decide(data.get('value_text'))
        if result['route'] == 'failure':
            raise RuntimeError('Jev decision failed')
        db.execute('INSERT INTO decisions VALUES (?,?,?,?)',
                   (event_id,result['route'],result['probability'],result['state_sha256']))
    return {'status':'stored',**result}

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/webhook':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length','0'))
        if not 0 < length <= 65536:
            self.send_error(413)
            return
        body = self.rfile.read(length)
        try:
            result = classify(body, self.headers, secret=os.environ['FORMBRICKS_WEBHOOK_SECRET'],
                              db_path=os.getenv('JEV_DB_PATH','decisions.sqlite3'),
                              question=os.environ['JEV_QUESTION'])
            status = 200
        except RuntimeError:
            result, status = {'error':'decision_unavailable'}, 503
        except Exception:
            result, status = {'error':'invalid_webhook'}, 401
        payload = json.dumps(result).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

def main():
    if not os.getenv('FORMBRICKS_WEBHOOK_SECRET') or not os.getenv('JEV_QUESTION'):
        raise SystemExit('FORMBRICKS_WEBHOOK_SECRET and JEV_QUESTION are required')
    db_path = Path(os.getenv('JEV_DB_PATH','decisions.sqlite3'))
    with connect(db_path):
        pass
    ThreadingHTTPServer(('0.0.0.0',int(os.getenv('PORT','8080'))),Handler).serve_forever()

if __name__ == '__main__':
    main()
