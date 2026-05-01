import unittest
import sys
import os
import importlib.util
from unittest.mock import patch

# Path to the daemon script
DAEMON_PATH = os.path.join(os.path.dirname(__file__), '..', 'transcription-daemon', 'geo-transcript-srv.py')

class TestDaemonUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Mock sys.argv to avoid ArgumentParser error during import
        with patch.object(sys, 'argv', ['geo-transcript-srv.py', '--geomdir', 'osml10n/boundaries']):
            spec = importlib.util.spec_from_file_location("geo_transcript_srv", DAEMON_PATH)
            cls.geo_transcript_srv = importlib.util.module_from_spec(spec)
            sys.modules["geo_transcript_srv"] = cls.geo_transcript_srv
            spec.loader.exec_module(cls.geo_transcript_srv)

    def test_contains_thai(self):
        self.assertTrue(self.geo_transcript_srv.contains_thai("ห้องสมุด"))
        self.assertFalse(self.geo_transcript_srv.contains_thai("Hello"))
        self.assertTrue(self.geo_transcript_srv.contains_thai("Hello ห้องสมุด"))

    def test_contains_cjk(self):
        self.assertTrue(self.geo_transcript_srv.contains_cjk("漢字"))
        self.assertFalse(self.geo_transcript_srv.contains_cjk("Hello"))
        self.assertTrue(self.geo_transcript_srv.contains_cjk("Hello 漢字"))

    def test_split_by_alphabet(self):
        res = self.geo_transcript_srv.split_by_alphabet("ABC漢字123")
        self.assertIsInstance(res, list)
        self.assertGreater(len(res), 0)

if __name__ == '__main__':
    unittest.main()
