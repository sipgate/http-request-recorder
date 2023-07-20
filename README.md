# HTTP Request recorder

A package to record and respond to http requests, primarily for use in black box testing.

## Basic Example

```python
from aiohttp import ClientSession

from http_request_recorder.http_request_recorder import HttpRequestRecorder

async with (
    HttpRequestRecorder('any_recorder_name', 8080) as recorder,
    ClientSession() as http_session
):
    expectation = recorder.expect_path(path='/any-path', responses=b'Hello back from recorder')

    await http_session.get('http://localhost:8080/any-path', data=b'Hello')

    recorded_request = await expectation.wait()

    print(recorded_request)  # prints "b'Hello'"
```

For more use cases, see the [tests file](./tests/test_http_request_recorder.py).
