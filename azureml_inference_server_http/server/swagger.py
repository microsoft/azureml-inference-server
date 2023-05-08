# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
import logging
import os
from typing import Any, Callable, ClassVar, Dict, Iterable, List, Optional, Set, Type, TypeVar

from inference_schema.schema_util import (
    get_input_schema,
    get_output_schema,
    get_supported_versions,
    is_schema_decorated,
)

from .config import config
from .exceptions import AzmlAssertionError
from .user_script import UserScript


logger = logging.getLogger("azmlinfsrv.swagger")

_SwaggerBuilderTypeT = TypeVar("_SwaggerBuilderTypeT", bound="Type[_SwaggerBuilder]")


class SwaggerException(Exception):
    """Swagger generation threw an exception."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class Swagger:
    _builder_classes: ClassVar[List[Type["_SwaggerBuilder"]]] = []

    # The set of swagger versions (and their aliases) we have builders for. Remember that some user scripts may not be
    # compatible with some versions of swagger. For example, swagger 2 does not support multi-type arrays.
    _valid_versions: ClassVar[Set[str]] = set()

    def __init__(self, app_root: str, server_root: str, user_script: UserScript):
        # These are the versions of swaggers (without aliases) that are available for this user script.
        self.supported_versions: List[str] = []

        # Maps a swagger version alias to the swagger JSON.
        self.swagger_jsons: Dict[str, dict] = {}

        # Get the swagger from each builder, and populate `supported_version` and `unsupported_versions`.
        unsupported_versions = []
        for builder_cls in self._builder_classes:
            builder = builder_cls(app_root, server_root, user_script)
            swagger_json = builder.get_swagger()
            if swagger_json is not None:
                for version in builder.__version_aliases__:
                    self.swagger_jsons[version] = swagger_json

                self.supported_versions.append(builder_cls.__version__)
            else:
                unsupported_versions.append(builder_cls.__version__)

        self.supported_versions.sort()
        unsupported_versions.sort()

        if self.supported_versions and unsupported_versions:
            logger.info(
                f"Swaggers are prepared for versions [{', '.join(self.supported_versions)}] "
                f"and skipped for versions [{', '.join(unsupported_versions)}]."
            )
        elif self.supported_versions:
            logger.info(f"Swaggers are prepared for the following versions: [{', '.join(self.supported_versions)}].")
        elif unsupported_versions:
            logger.info("No swagger is prepared.")

    @classmethod
    def _register_builder(
        cls, version: str, *, aliases: Iterable[str] = []
    ) -> Callable[[_SwaggerBuilderTypeT], _SwaggerBuilderTypeT]:
        def register(builder_cls: _SwaggerBuilderTypeT) -> _SwaggerBuilderTypeT:
            builder_cls.__version__ = version
            builder_cls.__version_aliases__ = {version, *aliases}
            cls._builder_classes.append(builder_cls)
            cls._valid_versions.update(builder_cls.__version_aliases__)
            return builder_cls

        return register

    def get_swagger(self, swagger_version: str) -> dict:
        if swagger_version not in self._valid_versions:
            raise SwaggerException(
                f"Swagger version [{swagger_version}] is not valid. "
                f"Supported versions: [{', '.join(sorted(self.supported_versions))}]."
            )

        swagger = self.swagger_jsons.get(swagger_version)
        if not swagger:
            raise SwaggerException(
                f"Swagger version [{swagger_version}] is not supported for the scoring script. "
                f"Supported swagger versions: [{', '.join(sorted(self.supported_versions))}]."
            )

        return swagger


class _SwaggerBuilder:
    # These are set by Swagger._register_builder()
    __version__: ClassVar[str]
    __version_aliases__: ClassVar[Set[str]]

    @property
    def swagger_template(self):
        return f"swagger{self.__version__}_template.json"

    def __init__(self, app_root: str, server_root: str, user_script: UserScript):
        self.app_root = app_root
        self.server_root = server_root
        self.user_script = user_script

    def _update_definitions(
        self, swagger_spec: dict, input_schema: Any, output_schema: Any
    ) -> None:  # pragma: no cover
        raise AzmlAssertionError("_update_definitions method is not overridden")

    def get_swagger(self) -> Optional[dict]:
        swagger_file = self._read_user_swagger()
        if not swagger_file:
            return self._generate_swagger()

        return swagger_file

    def _read_swagger(self, swagger_filename: str) -> Optional[dict]:
        swagger_path = os.path.join(self.app_root, swagger_filename)
        try:
            with open(swagger_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            logger.info(f"Loaded user's swagger file for version [{self.__version__}] from {swagger_path}")
        except FileNotFoundError:
            return None

        return data

    def _read_user_swagger(self) -> Optional[dict]:
        return self._read_swagger(f"swagger{self.__version__}.json")

    def _generate_swagger(self) -> Optional[dict]:
        run_function = self.user_script.get_run_function()

        # If request swagger version not supported, this will remain None
        if all(version not in get_supported_versions(run_function) for version in self.__version_aliases__):
            return None

        if is_schema_decorated(run_function):
            # run() is decorated. Get the input and output schema from inference-schema.
            input_schema = get_input_schema(run_function)
            output_schema = get_output_schema(run_function)
        else:
            # run() is not decorated. Set input and output schemas to empty objects.
            input_schema = output_schema = {"type": "object", "example": {}}
        template_path = os.path.join(self.server_root, self.swagger_template)
        with open(template_path, "r", encoding="utf-8") as f:
            swagger_spec_str = f.read()

        # Substitude special values in the template JSON.
        swagger_spec_str = (
            swagger_spec_str.replace("$SERVICE_NAME$", config.service_name)
            .replace("$SERVICE_VERSION$", config.service_version)
            .replace(
                "$PATH_PREFIX$", f"/{config.service_path_prefix.strip('/')}" if config.service_path_prefix else ""
            )
        )

        swagger_spec = json.loads(swagger_spec_str)
        self._update_definitions(swagger_spec, input_schema, output_schema)
        return swagger_spec


@Swagger._register_builder("2", aliases=["2.0"])
class Swagger2Builder(_SwaggerBuilder):
    def _read_user_swagger(self) -> Optional[dict]:
        swagger = super()._read_swagger("swagger.json")
        if swagger:
            return swagger

        return super()._read_user_swagger()

    def _update_definitions(self, swagger_spec: dict, input_schema: Any, output_schema: Any) -> None:
        swagger_spec["definitions"]["ServiceInput"] = input_schema
        swagger_spec["definitions"]["ServiceOutput"] = output_schema


@Swagger._register_builder("3", aliases=["3.0"])
class Swagger3Builder(_SwaggerBuilder):
    def _update_definitions(self, swagger_spec: dict, input_schema: Any, output_schema: Any) -> None:
        swagger_spec["components"]["schemas"]["ServiceInput"] = input_schema
        swagger_spec["components"]["schemas"]["ServiceOutput"] = output_schema


@Swagger._register_builder("3.1")
class Swagger31Builder(Swagger3Builder):
    @property
    def swagger_template(self):
        return "swagger3_template.json"

    def _update_definitions(self, swagger_spec: dict, input_schema: Any, output_schema: Any) -> None:
        super()._update_definitions(swagger_spec, input_schema, output_schema)
        swagger_spec["openapi"] = "3.1.0"
