import unittest
import sys
import os
import importlib.util
from unittest.mock import patch, MagicMock
import asyncio
import struct

# Path to the daemon script
DAEMON_PATH = os.path.join(os.path.dirname(__file__), '..', 'transcription-daemon', 'geo-transcript-srv.py')

class TestDaemon(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Mock sys.argv to avoid ArgumentParser error during import
        # We need a valid geomdir for Coord2Country to initialize
        geomdir = os.path.join(os.path.dirname(__file__), 'minimal_data', 'boundaries')
        with patch.object(sys, 'argv', ['geo-transcript-srv.py', '--geomdir', geomdir]):
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
        self.assertEqual(res, ["ABC", "漢字", "123"])

    def test_thai_transcript(self):
        res = self.geo_transcript_srv.thai_transcript("ห้องสมุด")
        self.assertIsNotNone(res)

    def test_thai_transcript_error(self):
        with patch('geo_transcript_srv.thai_romanize', side_effect=Exception("mock error")):
            res = self.geo_transcript_srv.thai_transcript("ห้องสมุด")
            self.assertIsNone(res)

    def test_cantonese_transcript(self):
        res = self.geo_transcript_srv.cantonese_transcript("香港")
        self.assertEqual(res, "hōeng góng")

    def test_cantonese_transcript_error(self):
        with patch('pinyin_jyutping_sentence.jyutping', side_effect=Exception("mock error")):
            res = self.geo_transcript_srv.cantonese_transcript("香港")
            self.assertIsNone(res)

    def test_transcriptor_kanji(self):
        tc = self.geo_transcript_srv.transcriptor(self.geo_transcript_srv.co2c.boundaries)
        res = tc.kanji_transcript("1", "jp", "東京")
        self.assertEqual(res, "Toukyou")

    def test_transcriptor_transcript(self):
        tc = self.geo_transcript_srv.transcriptor(self.geo_transcript_srv.co2c.boundaries)
        # Japan
        self.assertEqual(tc.transcript("1", "jp", "東京"), "Toukyou")
        # Thailand
        self.assertIsNotNone(tc.transcript("1", "th", "ห้องสมุด"))
        # HK/MO
        self.assertEqual(tc.transcript("1", "hk", "香港"), "hōeng góng")
        self.assertEqual(tc.transcript("1", "mo", "香港"), "hōeng góng")
        # Generic Any-Latin (ICU)
        self.assertEqual(tc.transcript("1", "ru", "Москва"), "Moskva")
        # Unknown country
        self.assertEqual(tc.transcript("1", "xx", "Москва"), "Moskva")

    def test_coord2country(self):
        co2c = self.geo_transcript_srv.co2c
        # Tokyo: 139.69, 35.69 (roughly)
        self.assertEqual(co2c.getCountry("1", "139.69", "35.69"), "jp")
        # Bangkok: 100.5, 13.75
        self.assertEqual(co2c.getCountry("1", "100.5", "13.75"), "th")
        # Unknown
        self.assertEqual(co2c.getCountry("1", "0", "0"), "")
        # Empty coords
        self.assertEqual(co2c.getCountry("1", "", ""), "")

    def test_read_boundaries_none(self):
        # This might fail if osml10n is not installed properly in the environment
        # We can mock resources.files if needed, but let's try to skip if it fails
        try:
            features = self.geo_transcript_srv.Coord2Country.read_boundaries(None)
            self.assertIsInstance(features, list)
            self.assertGreater(len(features), 0)
        except ModuleNotFoundError:
            self.skipTest("osml10n module not found for resources.files")

    async def test_handle_connection_cc(self):
        reader = MagicMock()
        writer = MagicMock()

        req = "CC/42/jp/東京"
        req_data = req.encode('utf-8')
        length_data = struct.pack('I', len(req_data))

        call_count = 0
        def read_side_effect(n):
            f = asyncio.Future()
            nonlocal call_count
            if call_count == 0:
                f.set_result(length_data)
                call_count += 1
            elif call_count == 1:
                f.set_result(req_data)
                call_count += 1
            else:
                if n == 4: f.set_result(b'')
                else: f.set_exception(asyncio.exceptions.IncompleteReadError(b'', n))
            return f
        reader.readexactly.side_effect = read_side_effect

        replies = []
        writer.write.side_effect = lambda d: replies.append(d)
        writer.drain.return_value = asyncio.Future()
        writer.drain.return_value.set_result(None)

        await self.geo_transcript_srv.handle_connection(reader, writer)

        self.assertGreater(len(replies), 0)
        resp_data = replies[0][4:].decode('utf-8')
        self.assertEqual(resp_data, "Toukyou")

    async def test_handle_connection_xy_cjk(self):
        reader = MagicMock()
        writer = MagicMock()

        req = "XY/42/139.69/35.69/東京"
        req_data = req.encode('utf-8')
        length_data = struct.pack('I', len(req_data))

        call_count = 0
        def read_side_effect(n):
            f = asyncio.Future()
            nonlocal call_count
            if call_count == 0:
                f.set_result(length_data)
                call_count += 1
            elif call_count == 1:
                f.set_result(req_data)
                call_count += 1
            else:
                if n == 4: f.set_result(b'')
                else: f.set_exception(asyncio.exceptions.IncompleteReadError(b'', n))
            return f
        reader.readexactly.side_effect = read_side_effect

        replies = []
        writer.write.side_effect = lambda d: replies.append(d)
        writer.drain.return_value = asyncio.Future()
        writer.drain.return_value.set_result(None)

        await self.geo_transcript_srv.handle_connection(reader, writer)
        self.assertGreater(len(replies), 0)
        resp_data = replies[0][4:].decode('utf-8')
        self.assertEqual(resp_data, "Toukyou")

    async def test_handle_connection_xy_thai(self):
        reader = MagicMock()
        writer = MagicMock()

        req = "XY/42/100.5/13.75/ห้องสมุด"
        req_data = req.encode('utf-8')
        length_data = struct.pack('I', len(req_data))

        call_count = 0
        def read_side_effect(n):
            f = asyncio.Future()
            nonlocal call_count
            if call_count == 0:
                f.set_result(length_data)
                call_count += 1
            elif call_count == 1:
                f.set_result(req_data)
                call_count += 1
            else:
                if n == 4: f.set_result(b'')
                else: f.set_exception(asyncio.exceptions.IncompleteReadError(b'', n))
            return f
        reader.readexactly.side_effect = read_side_effect

        replies = []
        writer.write.side_effect = lambda d: replies.append(d)
        writer.drain.return_value = asyncio.Future()
        writer.drain.return_value.set_result(None)

        await self.geo_transcript_srv.handle_connection(reader, writer)
        self.assertGreater(len(replies), 0)
        resp_data = replies[0][4:].decode('utf-8')
        self.assertIsNotNone(resp_data)

    async def test_handle_connection_unknown_cmd(self):
        reader = MagicMock()
        writer = MagicMock()

        req = "ZZ/unknown"
        req_data = req.encode('utf-8')
        length_data = struct.pack('I', len(req_data))

        call_count = 0
        def read_side_effect(n):
            f = asyncio.Future()
            nonlocal call_count
            if call_count == 0:
                f.set_result(length_data)
                call_count += 1
            elif call_count == 1:
                f.set_result(req_data)
                call_count += 1
            else:
                if n == 4: f.set_result(b'')
                else: f.set_exception(asyncio.exceptions.IncompleteReadError(b'', n))
            return f
        reader.readexactly.side_effect = read_side_effect

        replies = []
        writer.write.side_effect = lambda d: replies.append(d)
        writer.drain.return_value = asyncio.Future()
        writer.drain.return_value.set_result(None)

        await self.geo_transcript_srv.handle_connection(reader, writer)
        self.assertGreater(len(replies), 0)
        resp_data = replies[0][4:].decode('utf-8')
        self.assertEqual(resp_data, "")

    async def test_handle_connection_empty_name(self):
        reader = MagicMock()
        writer = MagicMock()

        req = "CC/42/jp/"
        req_data = req.encode('utf-8')
        length_data = struct.pack('I', len(req_data))

        call_count = 0
        def read_side_effect(n):
            f = asyncio.Future()
            nonlocal call_count
            if call_count == 0:
                f.set_result(length_data)
                call_count += 1
            elif call_count == 1:
                f.set_result(req_data)
                call_count += 1
            else:
                if n == 4: f.set_result(b'')
                else: f.set_exception(asyncio.exceptions.IncompleteReadError(b'', n))
            return f
        reader.readexactly.side_effect = read_side_effect

        replies = []
        writer.write.side_effect = lambda d: replies.append(d)
        writer.drain.return_value = asyncio.Future()
        writer.drain.return_value.set_result(None)

        await self.geo_transcript_srv.handle_connection(reader, writer)
        self.assertGreater(len(replies), 0)
        resp_data = replies[0][4:].decode('utf-8')
        self.assertEqual(resp_data, "")

    async def test_handle_connection_exception(self):
        reader = MagicMock()
        writer = MagicMock()

        req = "CC/42/jp/error"
        req_data = req.encode('utf-8')
        length_data = struct.pack('I', len(req_data))

        call_count = 0
        def read_side_effect(n):
            f = asyncio.Future()
            nonlocal call_count
            if call_count == 0:
                f.set_result(length_data)
                call_count += 1
            elif call_count == 1:
                f.set_result(req_data)
                call_count += 1
            else:
                if n == 4: f.set_result(b'')
                else: f.set_exception(asyncio.exceptions.IncompleteReadError(b'', n))
            return f
        reader.readexactly.side_effect = read_side_effect

        replies = []
        writer.write.side_effect = lambda d: replies.append(d)
        writer.drain.return_value = asyncio.Future()
        writer.drain.return_value.set_result(None)

        with patch.object(self.geo_transcript_srv.tc, 'transcript', side_effect=Exception("forced error")):
            await self.geo_transcript_srv.handle_connection(reader, writer)

        self.assertGreater(len(replies), 0)
        resp_data = replies[0][4:].decode('utf-8')
        self.assertEqual(resp_data, "")

if __name__ == '__main__':
    unittest.main()
