import asyncio
import contextlib
import re
from asyncio import Event
from itertools import tee
from logging import getLogger
from typing import Iterable, Union

from aiohttp import web
from aiohttp.web_request import BaseRequest

ResponsesType = Union[str, bytes, web.Response, Iterable[str], Iterable[bytes], Iterable[web.Response]]


class RecordedRequest:
    def __init__(self, ):
        self.body = None
        self.method = None
        self.path = None
        self.headers = None

    @staticmethod
    async def from_base_request(request: BaseRequest):
        recorded_request = RecordedRequest()

        recorded_request.body = await request.read()
        recorded_request.method = request.method
        recorded_request.path = request.path
        recorded_request.headers = request.headers

        return recorded_request


class ExpectedInteraction:
    class SingleRequest:
        def __init__(self, response):
            self.request = None
            self.was_triggered = Event()
            self.response = response

    def __init__(self, matcher, responses: ResponsesType, name: str, timeout: int):
        self.name: str = name
        self._timeout: int = timeout

        self.expected_count = None  # None: use infinitely
        if isinstance(responses, (str, bytes, web.Response)):
            self.responses = (ExpectedInteraction.SingleRequest(responses),)
            self.expected_count = 1
        elif isinstance(responses, Iterable):
            self.responses = map(ExpectedInteraction.SingleRequest, responses)
            if hasattr(responses, "__len__"):
                self.expected_count = sum(1 for _ in responses)
        else:
            raise TypeError("responses must be str | bytes | web.Response | Iterable[str] | Iterable[bytes] | Iterable[web.Response]")

        self._recorded = []
        self._next_for_response, self._next_to_return = tee(self.responses)
        self._matcher = matcher

    def __repr__(self):
        return f"<{self.__class__.__name__} '{self.name}'>"

    def record_once(self, request_body: bytes):
        for_response = next(self._next_for_response)
        for_response.request = request_body
        for_response.was_triggered.set()
        self._recorded.append(for_response)
        return for_response.response

    def is_still_expecting_requests(self):
        if self.expected_count is None:
            return False
        return len(self._recorded) < self.expected_count

    def can_respond(self, request: RecordedRequest):
        responds_infinitely = self.expected_count is None
        if responds_infinitely:
            will_respond = True
        else:
            will_respond = len(self._recorded) < self.expected_count

        return self._matcher(request) and will_respond

    async def wait(self) -> str:
        to_return = next(self._next_to_return)

        # suppress (not very helpful) stack of asyncio errors that get raised on timeout
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(to_return.was_triggered.wait(), self._timeout)
        if not to_return.was_triggered.is_set():
            # the above wait_for() timed out, raise a useful Exception:
            raise TimeoutError(f"{self} timed out waiting for a request")

        if to_return.request is None:
            raise LookupError("expected request body to be set")

        return to_return.request


class HttpRequestRecorder:
    def __init__(self, name: str, port: int):
        self._logger = getLogger("recorder")

        self._name = name
        self._port = port

        self._expectations: list[ExpectedInteraction] = []

        app = web.Application()

        app.add_routes([web.get('/{tail:.*}', self.handle_request)])
        app.add_routes([web.post('/{tail:.*}', self.handle_request)])
        app.add_routes([web.put('/{tail:.*}', self.handle_request)])
        app.add_routes([web.delete('/{tail:.*}', self.handle_request)])
        app.add_routes([web.options('/{tail:.*}', self.handle_request)])

        self.runner = web.AppRunner(app)

    def __repr__(self):
        return f"<{self.__class__.__name__} '{self._name}' on :{self._port}>"

    async def __aenter__(self):
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self._port)
        await site.start()

        return self

    async def __aexit__(self, *args, **kwargs):
        still_expecting = [exp for exp in self._expectations if exp.is_still_expecting_requests()]
        if len(still_expecting) > 0:
            self._logger.warning(f"{self} is exiting but there are unsatisfied Expectations: {still_expecting}")

        await self.runner.cleanup()

    async def handle_request(self, request: BaseRequest):
        request_body = await request.read()
        self._logger.info(f"{self} got {await self._request_string_for_log(request)}")

        recorded_request = await RecordedRequest.from_base_request(request)

        matches = [exp for exp in self._expectations if exp.can_respond(recorded_request)]
        if len(matches) == 0:
            self._logger.warning(f"{self} got unexpected {await self._request_string_for_log(request)}")
            return web.Response(status=404)

        if len(matches) > 1:
            error = f"{self} got a request that would match multiple expectations: {matches}"
            raise Exception(error)

        expectation_to_use = matches[0]
        response = expectation_to_use.record_once(request_body)

        if isinstance(response, web.Response):
            return response

        return web.Response(status=200, body=response)

    def expect(self, matcher, responses: ResponsesType = "", name: str = None, timeout: int = 3) -> ExpectedInteraction:
        expectation = ExpectedInteraction(matcher, responses, name, timeout)
        self._expectations.append(expectation)
        return expectation

    def expect_path(self, path: str, responses: ResponsesType = "", timeout: int = 3) -> ExpectedInteraction:
        return self.expect(lambda request: path == request.path, responses, name=path, timeout=timeout)

    def expect_xml_rpc(self, in_body: bytes, responses: ResponsesType = "", timeout: int = 3):
        # TODO: test
        def matcher(request):
            return "/RPC2" == request.path and in_body in request.body
        return self.expect(matcher,
                           responses=responses,
                           name=f"XmlRpc: {in_body.decode('UTF-8')}",
                           timeout=timeout)

    @staticmethod
    async def _request_string_for_log(request):
        request_body = await request.read()

        xml_rpc_method = re.search(b"<methodName>.*?</methodName>", request_body)
        if xml_rpc_method is not None:
            return f"{request.method} - XmlRpc - {xml_rpc_method.group(0).decode('UTF-8')}"

        json_rpc_method = re.search(b'"method":".*?"', request_body)
        if json_rpc_method is not None:
            return f"{request.method} - jsonRpc - {json_rpc_method.group(0).decode('UTF-8')}"

        return f"{request.method} to '{request.path}' with body '{request_body[:10]}'"
