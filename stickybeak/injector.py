import inspect
import json
import os
import pickle
import sys
import textwrap
from abc import ABC
from pathlib import Path
from typing import Callable, Dict, List, Type
from urllib.parse import urljoin, urlparse

import requests


class Injector(ABC):
    """Provides interface for code injection."""

    def __init__(
        self,
        address: str,
        endpoint: str = "stickybeak/",
        sources_dir: Path = Path(".remote_sources"),
    ) -> None:
        """
        :param address: service address that's gonna be injected.
        :param endpoint:
        """
        self.address: str = address
        self.endpoint: str = urljoin(self.address, endpoint)

        self.name: str = urlparse(self.address).netloc

        self.sources_dir: Path = sources_dir / Path(self.name)

        self._download_remote_code()

    def _download_remote_code(self) -> None:
        url: str = urljoin(self.endpoint, "source")
        response: requests.Response = requests.get(url)
        response.raise_for_status()

        sources: Dict[str, str] = json.loads(response.content)

        if sources == {}:
            raise RuntimeError("Couldn't find any source files (*.py).")

        for path, source in sources.items():
            abs_path: Path = self.sources_dir / Path(path)

            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.touch()
            abs_path.write_text(source)

    def _get_env_vars(self) -> os._Environ:  # type: ignore
        url: str = urljoin(self.endpoint, "envs")
        response: requests.Response = requests.get(url)
        response.raise_for_status()

        envs: Dict[str, str] = json.loads(response.content)

        environ = os._Environ(  # type: ignore
            data=envs,
            encodekey=lambda x: x,
            decodekey=lambda x: x,
            encodevalue=lambda x: x,
            decodevalue=lambda x: x,
            putenv=lambda k, v: None,
            unsetenv=lambda k, v: None,
        )

        return environ

    def execute_remote_code(self, code: str) -> bytes:
        url: str = urljoin(self.endpoint, "inject")
        code = self._add_try_except(code)

        headers: Dict[str, str] = {"Content-type": "application/json"}
        payload: Dict[str, str] = {"code": code}
        data: str = json.dumps(payload)

        response: requests.Response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()

        return response.content

    def run_code(self, code: str) -> Dict[str, object]:
        """Execute code.
        Returns:
            Dictionary containing all local variables.
        Raises:
            All exceptions from the code run remotely.
        Sample usage.
        >>> injector: Injector = Injector('http://testedservice.local')
        >>> injector.run_code('a = 1')
        """
        raise NotImplementedError

    def _get_fun_src(self, fun: Callable[[], None]) -> str:
        code: str = inspect.getsource(fun)

        code_lines: List[str] = code.splitlines(True)

        if "@" in code_lines[0]:
            code_lines.pop(0)

        code_lines.pop(0)

        code = "".join(code_lines)

        # remove indent that's left
        code = textwrap.dedent(code)

        return code

    def run_fun(self, fun: Callable[[], None]) -> Dict[str, object]:
        ret = self.run_code(self._get_fun_src(fun))
        return ret

    def klass(self, cls: Type) -> Type:  # type: ignore
        cls._injector = self
        methods: List[str] = [
            a for a in dir(cls) if not a.startswith("__") and callable(getattr(cls, a))
        ]

        for m in methods:
            method: Callable[[], None] = getattr(cls, m)
            fun_code: str = cls._injector._get_fun_src(method)
            setattr(cls, m, lambda: cls._injector.run_code(fun_code))

        return cls

    def function(self, fun: Callable[[], None]) -> Callable[[], Dict[str, object]]:
        """
        Decorator
        :param fun: function to be decorated:
        :return decorated function:
        """

        def wrapped() -> Dict[str, object]:
            ret = self.run_code(self._get_fun_src(fun))
            return ret

        return wrapped

    @staticmethod
    def _add_try_except(code: str) -> str:
        ret = textwrap.indent(
            code, "    "
        )  # use tabs instead of spaces, easier to debug
        code_lines = ret.splitlines(True)
        code_lines.insert(0, "try:\n")
        except_block = """\nexcept Exception as __exc:\n    __exception = __exc\n"""

        code_lines.append(except_block)

        ret = "".join(code_lines)
        return ret


class DjangoInjector(Injector):
    def __init__(
        self,
        address: str,
        django_settings_module: str,
        endpoint: str = "stickybeak/",
        sources_dir: Path = Path(".remote_sources"),
    ) -> None:
        super().__init__(address=address, endpoint=endpoint, sources_dir=sources_dir)
        self.django_settings_module = django_settings_module

    def run_code(self, code: str) -> Dict[str, object]:
        # we have to unload all the django modules so django accepts the new configuration
        # make a module copy so we can iterate over it and delete modules from the original one

        # unload django
        modules = list(sys.modules.keys())[:]
        for m in modules:
            if "django" in m:
                sys.modules.pop(m)

        modules_before: List[str] = list(sys.modules.keys())[:]
        sys.path.append(str(self.sources_dir.absolute()))

        os.environ["DJANGO_SETTINGS_MODULE"] = self.django_settings_module

        import django

        env_vars_local: os._Environ = os.environ  # type: ignore
        env_vars_remote: os._Environ = self._get_env_vars()  # type: ignore
        os.environ = env_vars_remote

        django.setup()
        content: bytes = self.execute_remote_code(code)

        ret: Dict[str, object] = pickle.loads(content)

        os.environ = env_vars_local

        sys.path.remove(str(self.sources_dir.absolute()))
        del os.environ["DJANGO_SETTINGS_MODULE"]
        modules_after: List[str] = list(sys.modules.keys())[:]

        diff: List[str] = list(set(modules_after) - set(modules_before))

        for m in diff:
            sys.modules.pop(m)

        # handle exceptions
        if "__exception" in ret:
            raise ret["__exception"]  # type: ignore

        return ret


class FlaskInjector(Injector):
    def run_code(self, code: str) -> Dict[str, object]:
        # we have to unload all the django modules so django accepts the new configuration
        # make a module copy so we can iterate over it and delete modules from the original one
        modules_before: List[str] = list(sys.modules.keys())[:]

        sys.path.append(str(self.sources_dir.absolute()))

        content: bytes = self.execute_remote_code(code)
        ret: Dict[str, object] = pickle.loads(content)

        sys.path.remove(str(self.sources_dir.absolute()))

        modules_after: List[str] = list(sys.modules.keys())[:]
        diff: List[str] = list(set(modules_after) - set(modules_before))
        for m in diff:
            sys.modules.pop(m)

        # handle exceptions
        if "__exception" in ret:
            raise ret["__exception"]  # type: ignore

        return ret
