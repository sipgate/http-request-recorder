import logging
import unittest

from http_request_recorder import HttpRequestRecorder

from aiohttp import ClientSession

logging.basicConfig(encoding='utf-8', level=logging.INFO)


class TestHttpRequestRecorder(unittest.IsolatedAsyncioTestCase):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.port = 18080

    async def test_xml_rpc_method_not_found(self) -> None:
        async with (HttpRequestRecorder(name="testrecorder", port=self.port) as recorder,
                    ClientSession() as http_session):
            recorder.expect_xml_rpc(b'any_method', responses="<anyXml>")

            response = await http_session.post(f"http://localhost:{self.port}/RPC2", data="<methodCall><methodName>another_method</methodName><params></params></methodCall>")

            self.assertEqual(404, response.status)

    async def test_xml_rpc_malformed_call(self) -> None:
        async with (HttpRequestRecorder(name="testrecorder", port=self.port) as recorder,
                    ClientSession() as http_session):
            recorder.expect_xml_rpc(b'any_method', responses="<anyXml>")

            response = await http_session.post(f"http://localhost:{self.port}/RPC2", data="<methodCall>any_method<params></params></methodCall>")

            self.assertEqual(404, response.status)

    async def test_xml_rpc_return_response(self) -> None:
        async with (HttpRequestRecorder(name="testrecorder", port=self.port) as recorder,
                    ClientSession() as http_session):
            recorder.expect_xml_rpc(b'any_method', responses="<anyXml>")

            response = await http_session.post(f"http://localhost:{self.port}/RPC2", data="<methodCall><methodName>any_method</methodName><params></params></methodCall>")

            self.assertEqual(200, response.status)
            self.assertEqual(b"<anyXml>", await response.content.read())
