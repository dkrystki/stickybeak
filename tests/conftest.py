import json
import os
from pathlib import Path

import pytest
from furl import furl
from requests import Response

from stickybeak import handle_requests
from stickybeak.injector import DjangoInjector, FlaskInjector

flask_srv: str
django_srv: str
local_srv: str

flask_srv: str = f"http://{os.environ['FLASK_SRV_HOST']}:{os.environ['FLASK_SRV_PORT']}"
django_srv: str = f"http://{os.environ['DJANGO_SRV_HOSTNAME']}"
local_srv: str = "http://local-mock"


@pytest.fixture(params=[flask_srv, django_srv, local_srv])
def injector(request, mocker):
    if request.param == local_srv:

        def mock_post(endpoint: str, data: str, headers: dict) -> Response:
            result: bytes = handle_requests.inject(json.loads(data))
            response = Response()
            response._content = result
            response.status_code = 200
            return response

        def mock_get(endpoint: str) -> Response:
            url: furl = furl(endpoint)
            response = Response()

            if url.path.segments[-1] == "source":
                response._content = json.dumps(
                    handle_requests.get_source(Path("test_srvs/django_srv"))
                )
            elif url.path.segments[-1] == "envs":
                response._content = json.dumps(handle_requests.get_envs())
            response.status_code = 200
            return response

        post_mock = mocker.patch("requests.post")
        post_mock.side_effect = mock_post

        get_mock = mocker.patch("requests.get")
        get_mock.side_effect = mock_get

        return DjangoInjector(
            address=request.param, django_settings_module="django_srv.settings"
        )

    if request.param == django_srv:
        return DjangoInjector(
            address=request.param, django_settings_module="django_srv.settings"
        )

    if request.param == flask_srv:
        return FlaskInjector(address=request.param)


@pytest.fixture(scope="class")
def django_injector(request):
    request.cls.injector = DjangoInjector(
        address=django_srv, django_settings_module="django_srv.settings"
    )
