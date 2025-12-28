from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ErrorCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ERROR_CODE_UNSPECIFIED: _ClassVar[ErrorCode]
    ERROR_CODE_INVALID_ARGUMENTS: _ClassVar[ErrorCode]
    ERROR_CODE_SERVICE_UNAVAILABLE: _ClassVar[ErrorCode]
    ERROR_CODE_TOOL_NOT_FOUND: _ClassVar[ErrorCode]
    ERROR_CODE_INTERNAL_ERROR: _ClassVar[ErrorCode]

ERROR_CODE_UNSPECIFIED: ErrorCode
ERROR_CODE_INVALID_ARGUMENTS: ErrorCode
ERROR_CODE_SERVICE_UNAVAILABLE: ErrorCode
ERROR_CODE_TOOL_NOT_FOUND: ErrorCode
ERROR_CODE_INTERNAL_ERROR: ErrorCode

class ListToolsRequest(_message.Message):
    __slots__ = ("category",)
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    category: str
    def __init__(self, category: _Optional[str] = ...) -> None: ...

class ListToolsResponse(_message.Message):
    __slots__ = ("tools",)
    TOOLS_FIELD_NUMBER: _ClassVar[int]
    tools: _containers.RepeatedCompositeFieldContainer[ToolDefinition]
    def __init__(self, tools: _Optional[_Iterable[_Union[ToolDefinition, _Mapping]]] = ...) -> None: ...

class ToolDefinition(_message.Message):
    __slots__ = ("name", "description", "input_schema_json", "category")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    INPUT_SCHEMA_JSON_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    input_schema_json: str
    category: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        description: _Optional[str] = ...,
        input_schema_json: _Optional[str] = ...,
        category: _Optional[str] = ...,
    ) -> None: ...

class ToolCallRequest(_message.Message):
    __slots__ = ("tool_name", "arguments_json", "trace_id", "caller_agent_id")
    TOOL_NAME_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_JSON_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    CALLER_AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    tool_name: str
    arguments_json: str
    trace_id: str
    caller_agent_id: str
    def __init__(
        self,
        tool_name: _Optional[str] = ...,
        arguments_json: _Optional[str] = ...,
        trace_id: _Optional[str] = ...,
        caller_agent_id: _Optional[str] = ...,
    ) -> None: ...

class ToolCallResponse(_message.Message):
    __slots__ = ("success", "result_json", "error_code", "error_message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    RESULT_JSON_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    result_json: str
    error_code: ErrorCode
    error_message: str
    def __init__(
        self,
        success: bool = ...,
        result_json: _Optional[str] = ...,
        error_code: _Optional[_Union[ErrorCode, str]] = ...,
        error_message: _Optional[str] = ...,
    ) -> None: ...
