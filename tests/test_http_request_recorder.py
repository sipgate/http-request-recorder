import asyncio
import logging
import unittest

from aiohttp import web, ClientSession

from http_request_recorder.http_request_recorder import HttpRequestRecorder

logging.basicConfig(encoding='utf-8', level=logging.INFO)


# - [x] mehrere endpoints pro port
# - [x] Beliebig oft(functions.xml)) die gleiche response auf endpoint (0..n)
# - [x] Mehrere (unterschiedliche) Antworten hintereinander auf denselben Request?
# - [x] eine response pro request pro endpoint
# - [x] loggen von allen (level=~~DEBUG~~ INFO)
# - [?] loggen von nicht gehandelten (level=WARN)
# - - [] ...vertesten
# - [x] loggen von nicht eintreten von erwarteten requests (timeout) (level=WARN)
# - [x] Matchen auf Request.Body
# - [] expect_json_rpc(method_name="cron")-Helper (...nachdem wir ihn dreimal mit lambdas gebaut haben)
# - [x] expect_xml_rpc()
# - - [] ...vertesten
# - [x] Warnen, wenn mehrere Matcher passen
# - [] .wait_for_all() statt alles einzeln awaiten
# - [] Wo schneiden zwischen bytes (TCP/HTTP) und string (python)? (Wahrscheinlich überall bytes -für raw http?)


class TestHttpRequestRecorder(unittest.IsolatedAsyncioTestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.port = 18080

    async def test_recorder_with_no_routes_yields_404(self):
        async with (HttpRequestRecorder(name="testrecorder", port=self.port),
                    ClientSession() as http_session):
            response = await http_session.get(f"http://localhost:{self.port}/")

            self.assertEqual(404, response.status)

    async def test_recorder_with_a_route_returns_given_response(self):
        async with (HttpRequestRecorder(name="testrecorder", port=self.port) as recorder,
                    ClientSession() as http_session):
            recorder.expect_path(path="/path", responses="response")

            response = await http_session.get(f"http://localhost:{self.port}/path")

            self.assertEqual(200, response.status)
            self.assertEqual(b"response", await response.content.read())

    async def test_recorder_with_a_route_records_request(self):
        async with (HttpRequestRecorder(name="testrecorder", port=self.port) as recorder,
                    ClientSession() as http_session):
            expectation = recorder.expect_path(path="/path", responses="response")

            await http_session.post(f"http://localhost:{self.port}/path", data='testbody')

            recorded_request = await expectation.wait()

            self.assertEqual(b'testbody', recorded_request)

    async def test_recorder_records_requests_to_different_paths(self):
        async with (HttpRequestRecorder(name="testrecorder", port=self.port) as recorder,
                    ClientSession() as http_session):
            expectation1 = recorder.expect_path(path="/path1", responses="response1")
            expectation3 = recorder.expect_path(path="/path2", responses="response3")

            response1 = await http_session.post(f"http://localhost:{self.port}/path1", data='testbody1')
            response3 = await http_session.post(f"http://localhost:{self.port}/path2", data='testbody3')

            recorded_request1 = await expectation1.wait()
            recorded_request3 = await expectation3.wait()

            self.assertEqual(b'testbody1', recorded_request1)
            self.assertEqual(b'testbody3', recorded_request3)

            self.assertEqual(b'response1', await response1.content.read())
            self.assertEqual(b'response3', await response3.content.read())

    async def test_multiple_replies_to_same_path(self):
        async with (HttpRequestRecorder(name="multi-responding recorder", port=self.port) as recorder,
                    ClientSession() as http_session):
            responses = ("response_0", "response_1", "response_2")

            expectation = recorder.expect_path(path="/single_path", responses=responses)

            response1 = await http_session.post(f"http://localhost:{self.port}/single_path", data="req1")
            await http_session.post(f"http://localhost:{self.port}/single_path")
            response3 = await http_session.post(f"http://localhost:{self.port}/single_path", data="req3")

            recorded_request1 = await expectation.wait()
            await expectation.wait()
            recorded_request3 = await expectation.wait()

            self.assertEqual(b'req1', recorded_request1)
            self.assertEqual(b'req3', recorded_request3)

            self.assertEqual(b'response_0', await response1.content.read())
            self.assertEqual(b'response_2', await response3.content.read())

    # TODO: error on more requests to route than prepared/expected responses

    async def test_successful_response_logs_debug_message(self):
        with self.assertLogs("recorder", level=logging.INFO) as log_recorder:
            logging.getLogger("recorder").addHandler(logging.StreamHandler())

            async with (HttpRequestRecorder(name="logging recorder", port=self.port) as recorder,
                        ClientSession() as http_session):
                request_path = "/log_me"
                recorder.expect_path(path=request_path, responses="response_with_logging")
                await http_session.put(f"http://localhost:{self.port}/log_me")

            logs = log_recorder.output
            self.assertEqual(1, len(logs))
            self.assertIn(request_path, logs[0])
            self.assertIn("PUT", logs[0])

    async def test_log_warning_for_unrequested_expected_request(self):
        with self.assertLogs("recorder", level=logging.INFO) as log_recorder:
            logging.getLogger("recorder").addHandler(logging.StreamHandler())

            request_paths = ["/never_gets_called", "/neither"]
            async with HttpRequestRecorder(name="disappointed recorder", port=self.port) as recorder:

                for path in request_paths:
                    recorder.expect_path(path=path, responses="unused response")
                # no request is sent.

            logs = log_recorder.records
            self.assertEqual(1, len(logs))

            record = logs[0]
            self.assertEqual(logging.WARN, record.levelno)
            self.assertIn("never", record.msg)
            for path in request_paths:
                self.assertIn(path, record.msg)

    async def test_should_handle_late_request(self):
        async with HttpRequestRecorder(name="patient recorder", port=self.port) as recorder, ClientSession() as http_session:
            expectation = recorder.expect_path(path='/called-late', responses="response")

            async def late_post_request():
                await asyncio.sleep(0.2)
                await http_session.post(f"http://localhost:{self.port}/called-late", data='late_data')

            recorded_request, _ = await asyncio.gather(
                expectation.wait(),
                late_post_request())

            self.assertIn(b'late_data', recorded_request)

    # TODO: re-enable and define assertion(s)
    async def disabled_test_timeout_on_unrequested_expected_request(self):
        async with HttpRequestRecorder(name="disappointed recorder", port=self.port) as recorder:
            expectation = recorder.expect_path(path='never called', responses="unused response")
            # no request is sent.

            await expectation.wait()


    async def test_matching_on_body(self):
        async with (HttpRequestRecorder(name="different body recorder", port=self.port) as recorder,
                    ClientSession() as http_session):
            recorder.expect(lambda request: b"foo" in request.body, responses="foo called", name="foo-matcher")
            recorder.expect(lambda request: b"bar" in request.body, responses="bar called")

            bar_response = await http_session.post(f"http://localhost:{self.port}/rpc", data='bar')
            foo_response = await http_session.post(f"http://localhost:{self.port}/rpc", data='foo')

            foo_response_body = await foo_response.read()
            bar_response_body = await bar_response.read()

            self.assertIn(b"foo", foo_response_body)
            self.assertIn(b"bar", bar_response_body)

    async def test_exception_for_ambiguous_matching(self):
        with self.assertLogs("aiohttp", level=logging.ERROR) as aiohttp_recorder:
            logging.getLogger("aiohttp").addHandler(logging.StreamHandler())

            async with (HttpRequestRecorder(name="confused recorder", port=self.port) as recorder,
                        ClientSession() as http_session):
                recorder.expect_path(path="/path")
                recorder.expect(lambda request: b"body" in request.body, name="body-matcher")

                response = await http_session.post(f"http://localhost:{self.port}/path", data='body 1')
                await http_session.post(f"http://localhost:{self.port}/path", data='body 2')

                self.assertEqual(500, response.status)  # aiohttp catches our Exception and returns 500

            logs = aiohttp_recorder.records
            self.assertEqual(2, len(logs))

            record = logs[0]
            self.assertIn("Error handling request", record.msg)

    async def test_bytes_response(self):
        async with (HttpRequestRecorder(name="byte-returning recorder", port=self.port) as recorder,
                    ClientSession() as http_session):
            recorder.expect_path("/", b'nom.')

            response = await http_session.post(f"http://localhost:{self.port}/")

            self.assertEqual(b'nom.', await response.read())

    async def test_native_response(self):
        async with (HttpRequestRecorder(name="native-response-returning recorder", port=self.port) as recorder,
                    ClientSession() as http_session):
            recorder.expect_path("/", web.Response(status=214, body='{}', content_type='application/json'))

            response = await http_session.post(f"http://localhost:{self.port}/")

            self.assertEqual(214, response.status)
            self.assertEqual('application/json', response.content_type)
            self.assertEqual(b'{}', await response.read())

    async def test_responds_infinitely(self):
        # neither "unexpected" nor "unsatisfied"
        with self.assertNoLogs("recorder", level=logging.WARNING):
            logging.getLogger("recorder").addHandler(logging.StreamHandler())

            async with (HttpRequestRecorder(name="infinite responder", port=self.port) as recorder,
                        ClientSession() as http_session):
                def inifinite_responses():
                    while True:
                        yield b'on and on...'

                recorder.expect_path("/", inifinite_responses())

                for _ in range(10):
                    await http_session.post(f"http://localhost:{self.port}/")

    async def test_matches_on_headers(self):
        async with (HttpRequestRecorder(name="header-sensitive recorder", port=self.port) as recorder,
                    ClientSession() as http_session):
            foo_expect = recorder.expect(lambda req: "foo" in req.headers, "foo-response")

            bar_response = await http_session.post(f"http://localhost:{self.port}/", headers={"bar": "42"})
            foo_response = await http_session.post(f"http://localhost:{self.port}/",
                                                   headers={"foo": "23"},
                                                   data="foo-data")

            self.assertEqual(404, bar_response.status)
            self.assertEqual(200, foo_response.status)

            recorded_foo_request = await foo_expect.wait()
            self.assertEqual(recorded_foo_request, b'foo-data')
