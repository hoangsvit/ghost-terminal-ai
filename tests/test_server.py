import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from app import GhostHandler


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), GhostHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def req(self, method, path, data=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        conn.request(method, path, body=json.dumps(data) if data is not None else None, headers=headers or {'Content-Type':'application/json'})
        res = conn.getresponse()
        raw = res.read()
        status = res.status
        conn.close()
        return status, json.loads(raw) if res.getheader('Content-Type', '').startswith('application/json') else raw

    def test_html(self):
        status, html = self.req('GET','/')
        self.assertEqual(status,200)
        self.assertIn(b'Find the ghost',html)

    def test_scenario_catalog_served(self):
        status, body = self.req('GET', '/scenarios.js')
        self.assertEqual(status, 200)
        self.assertIn(b'TEST_SCENARIOS', body)

    def test_traversal_not_served(self):
        status, _ = self.req('GET','/../../app.py')
        self.assertEqual(status,404)

    def test_blank_input(self):
        status, payload = self.req('POST','/api/interpret', {'log':'  ', 'mode':'haunting'})
        self.assertEqual(status,400)
        self.assertIn('at least one',payload['error'])

    def test_cross_origin_rejected(self):
        status, _ = self.req('POST','/api/interpret', {'log':'git status'}, {'Content-Type':'application/json','Origin':'https://evil.example'})
        self.assertEqual(status,403)

    def test_end_to_end_with_fake_model(self):
        fake_story = {'title':'The old worker','transmission':'A lonely process waited.','whisper':'I am still here.', 'echoes':[{'fragment':'git status','meaning':'Looking for a trace'}]}
        with patch('app.generate_story', return_value=fake_story):
            status, response = self.req('POST','/api/interpret', {'log':'git status\npassword=abcdef', 'mode':'memory'})
        self.assertEqual(status,200)
        self.assertEqual(response['redactions'],1)
        self.assertEqual(response['story']['title'],'The old worker')

if __name__ == '__main__': unittest.main()
