from aiohttp import ClientSession

from http_request_recorder.http_request_recorder import HttpRequestRecorder


async def main():
    async with (
        HttpRequestRecorder('any_recorder_name', 8080) as recorder,
        ClientSession() as http_session
    ):
        expectation = recorder.expect_path(path='/any-path', responses=b'Hello back from recorder')

        await http_session.get('http://localhost:8080/any-path', data=b'Hello')

        recorded_request = await expectation.wait()

        print(recorded_request)  # prints "b'Hello'"


if __name__ == '__main__':
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
