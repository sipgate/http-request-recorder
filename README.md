# HTTP Request recorder

A package to record and respond to http requests, primarily for use in black box testing.

## Usage
In order to include this module in your project, add e.g.

`http_request_recorder @ git+https://github.com/sipgates/http-request-recorder.git@main`

to your `requirements.txt`.

### Basic Example

```python
from aiohttp import ClientSession

from http_request_recorder.http_request_recorder import HttpRequestRecorder

async with (
    HttpRequestRecorder('any_recorder_name', 8080) as recorder,
    ClientSession() as http_session
):
    expectation = recorder.expect_path(
        path='/any-path', # path to respond to
        responses=b'Hello back from recorder', # responses to return, can be a list
        name = 'any name', # optional name for the expected interaction
        timeout = 1, # optional timeout in seconds, defaults to 3
    )

    await http_session.get('http://localhost:8080/any-path', data=b'Hello')

    recorded_request = await expectation.wait()

    print(recorded_request)  # prints "b'Hello'"
```

For more use cases, see the [tests file](./tests/test_http_request_recorder.py).

### Native Responses

For advanced use cases, native `aiohttp` `web.Response` objects can be used as responses.
This allows specifying a content type or custom status codes.
