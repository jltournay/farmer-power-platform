from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ExtractionRequest(_message.Message):
    __slots__ = ("raw_content", "ai_agent_id", "source_config_json", "content_type", "trace_id")
    RAW_CONTENT_FIELD_NUMBER: _ClassVar[int]
    AI_AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_CONFIG_JSON_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    raw_content: str
    ai_agent_id: str
    source_config_json: str
    content_type: str
    trace_id: str
    def __init__(self, raw_content: _Optional[str] = ..., ai_agent_id: _Optional[str] = ..., source_config_json: _Optional[str] = ..., content_type: _Optional[str] = ..., trace_id: _Optional[str] = ...) -> None: ...

class ExtractionResponse(_message.Message):
    __slots__ = ("success", "extracted_fields_json", "confidence", "validation_passed", "validation_warnings", "error_message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    EXTRACTED_FIELDS_JSON_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    VALIDATION_PASSED_FIELD_NUMBER: _ClassVar[int]
    VALIDATION_WARNINGS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    extracted_fields_json: str
    confidence: float
    validation_passed: bool
    validation_warnings: _containers.RepeatedScalarFieldContainer[str]
    error_message: str
    def __init__(self, success: bool = ..., extracted_fields_json: _Optional[str] = ..., confidence: _Optional[float] = ..., validation_passed: bool = ..., validation_warnings: _Optional[_Iterable[str]] = ..., error_message: _Optional[str] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("healthy", "version")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    version: str
    def __init__(self, healthy: bool = ..., version: _Optional[str] = ...) -> None: ...
