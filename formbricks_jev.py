"""Signed Formbricks Hub webhook receiver with idempotent SQLite decisions."""
import json
import hmac
import os
import sqlite3
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from standardwebhooks.webhooks import Webhook, WebhookVerificationError
from jev_common import JevClient

@contextmanager
def connect(path):
    db = sqlite3.connect(path, timeout=15)
    db.execute('PRAGMA busy_timeout=15000')
    db.execute('CREATE TABLE IF NOT EXISTS decisions (event_id TEXT PRIMARY KEY, route TEXT NOT NULL, probability REAL, state_sha256 TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS claims (event_id TEXT PRIMARY KEY, claimed_at REAL NOT NULL)')
    try:
        with db:
            yield db
    finally:
        db.close()

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
        db.execute('DELETE FROM claims WHERE claimed_at < ?', (time.time() - 120,))
        claimed = db.execute('INSERT OR IGNORE INTO claims VALUES (?,?)', (event_id,time.time())).rowcount
    if not claimed:
        raise RuntimeError('Webhook is already being processed')
    try:
        judge = client or JevClient(question)
        result = judge.decide(data.get('value_text'))
        if result['route'] == 'failure':
            raise RuntimeError('Jev decision failed')
        with connect(db_path) as db:
            db.execute('INSERT OR IGNORE INTO decisions VALUES (?,?,?,?)',
                       (event_id,result['route'],result['probability'],result['state_sha256']))
            db.execute('DELETE FROM claims WHERE event_id=?', (event_id,))
    except Exception:
        with connect(db_path) as db:
            db.execute('DELETE FROM claims WHERE event_id=?', (event_id,))
        raise
    return {'status':'stored',**result}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/healthz':
            self._reply(200, {'status':'ok'})
            return
        if parsed.path != '/decisions':
            self.send_error(404)
            return
        token = os.getenv('FORMBRICKS_JEV_ADMIN_TOKEN')
        if not token or not hmac.compare_digest(self.headers.get('Authorization',''), 'Bearer ' + token):
            self._reply(401, {'error':'unauthorized'})
            return
        event_ids = parse_qs(parsed.query).get('event_id', [])
        if len(event_ids) != 1 or not 0 < len(event_ids[0]) <= 200:
            self._reply(400, {'error':'invalid_event_id'})
            return
        with connect(os.getenv('JEV_DB_PATH','decisions.sqlite3')) as db:
            row = db.execute('SELECT route,probability,state_sha256 FROM decisions WHERE event_id=?', (event_ids[0],)).fetchone()
        if not row:
            self._reply(404, {'error':'not_found'})
            return
        self._reply(200, {'event_id':event_ids[0],'route':row[0],'probability':row[1],'state_sha256':row[2]})

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
        except WebhookVerificationError:
            result, status = {'error':'invalid_signature'}, 401
        except (ValueError, json.JSONDecodeError):
            result, status = {'error':'invalid_webhook'}, 400
        except (RuntimeError, sqlite3.Error):
            result, status = {'error':'decision_unavailable'}, 503
        except Exception:
            result, status = {'error':'internal_error'}, 500
        self._reply(status, result)

    def _reply(self, status, result):
        payload = json.dumps(result).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass

def main():
    if not os.getenv('FORMBRICKS_WEBHOOK_SECRET') or not os.getenv('JEV_QUESTION'):
        raise SystemExit('FORMBRICKS_WEBHOOK_SECRET and JEV_QUESTION are required')
    db_path = Path(os.getenv('JEV_DB_PATH','decisions.sqlite3'))
    with connect(db_path):
        pass
    ThreadingHTTPServer(('0.0.0.0',int(os.getenv('PORT','8080'))),Handler).serve_forever()

if __name__ == '__main__':
    main()
