import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

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

class DateRangeRequest(_message.Message):
    __slots__ = ("start_date", "end_date")
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    start_date: _timestamp_pb2.Timestamp
    end_date: _timestamp_pb2.Timestamp
    def __init__(self, start_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., end_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CostSummaryResponse(_message.Message):
    __slots__ = ("total_cost_usd", "total_requests", "total_tokens_in", "total_tokens_out")
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    TOTAL_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_IN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_OUT_FIELD_NUMBER: _ClassVar[int]
    total_cost_usd: str
    total_requests: int
    total_tokens_in: int
    total_tokens_out: int
    def __init__(self, total_cost_usd: _Optional[str] = ..., total_requests: _Optional[int] = ..., total_tokens_in: _Optional[int] = ..., total_tokens_out: _Optional[int] = ...) -> None: ...

class DailyCost(_message.Message):
    __slots__ = ("date", "total_cost_usd", "total_requests", "total_tokens_in", "total_tokens_out", "success_count", "failure_count")
    DATE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    TOTAL_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_IN_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_OUT_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_COUNT_FIELD_NUMBER: _ClassVar[int]
    FAILURE_COUNT_FIELD_NUMBER: _ClassVar[int]
    date: _timestamp_pb2.Timestamp
    total_cost_usd: str
    total_requests: int
    total_tokens_in: int
    total_tokens_out: int
    success_count: int
    failure_count: int
    def __init__(self, date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., total_cost_usd: _Optional[str] = ..., total_requests: _Optional[int] = ..., total_tokens_in: _Optional[int] = ..., total_tokens_out: _Optional[int] = ..., success_count: _Optional[int] = ..., failure_count: _Optional[int] = ...) -> None: ...

class DailyCostSummaryResponse(_message.Message):
    __slots__ = ("daily_costs",)
    DAILY_COSTS_FIELD_NUMBER: _ClassVar[int]
    daily_costs: _containers.RepeatedCompositeFieldContainer[DailyCost]
    def __init__(self, daily_costs: _Optional[_Iterable[_Union[DailyCost, _Mapping]]] = ...) -> None: ...

class AgentTypeCostEntry(_message.Message):
    __slots__ = ("agent_type", "total_cost_usd", "total_requests", "total_tokens")
    AGENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    TOTAL_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
    agent_type: str
    total_cost_usd: str
    total_requests: int
    total_tokens: int
    def __init__(self, agent_type: _Optional[str] = ..., total_cost_usd: _Optional[str] = ..., total_requests: _Optional[int] = ..., total_tokens: _Optional[int] = ...) -> None: ...

class CostByAgentTypeResponse(_message.Message):
    __slots__ = ("agent_type_costs",)
    AGENT_TYPE_COSTS_FIELD_NUMBER: _ClassVar[int]
    agent_type_costs: _containers.RepeatedCompositeFieldContainer[AgentTypeCostEntry]
    def __init__(self, agent_type_costs: _Optional[_Iterable[_Union[AgentTypeCostEntry, _Mapping]]] = ...) -> None: ...

class ModelCostEntry(_message.Message):
    __slots__ = ("model", "total_cost_usd", "total_requests", "total_tokens")
    MODEL_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    TOTAL_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
    model: str
    total_cost_usd: str
    total_requests: int
    total_tokens: int
    def __init__(self, model: _Optional[str] = ..., total_cost_usd: _Optional[str] = ..., total_requests: _Optional[int] = ..., total_tokens: _Optional[int] = ...) -> None: ...

class CostByModelResponse(_message.Message):
    __slots__ = ("model_costs",)
    MODEL_COSTS_FIELD_NUMBER: _ClassVar[int]
    model_costs: _containers.RepeatedCompositeFieldContainer[ModelCostEntry]
    def __init__(self, model_costs: _Optional[_Iterable[_Union[ModelCostEntry, _Mapping]]] = ...) -> None: ...

class CostAlert(_message.Message):
    __slots__ = ("threshold_type", "threshold_usd", "current_cost_usd", "triggered_at", "event_id")
    THRESHOLD_TYPE_FIELD_NUMBER: _ClassVar[int]
    THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    CURRENT_COST_USD_FIELD_NUMBER: _ClassVar[int]
    TRIGGERED_AT_FIELD_NUMBER: _ClassVar[int]
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    threshold_type: str
    threshold_usd: str
    current_cost_usd: str
    triggered_at: _timestamp_pb2.Timestamp
    event_id: str
    def __init__(self, threshold_type: _Optional[str] = ..., threshold_usd: _Optional[str] = ..., current_cost_usd: _Optional[str] = ..., triggered_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., event_id: _Optional[str] = ...) -> None: ...

class CostAlertsResponse(_message.Message):
    __slots__ = ("alerts", "daily_threshold_usd", "daily_total_usd", "daily_alert_triggered", "monthly_threshold_usd", "monthly_total_usd", "monthly_alert_triggered")
    ALERTS_FIELD_NUMBER: _ClassVar[int]
    DAILY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    DAILY_TOTAL_USD_FIELD_NUMBER: _ClassVar[int]
    DAILY_ALERT_TRIGGERED_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_TOTAL_USD_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_ALERT_TRIGGERED_FIELD_NUMBER: _ClassVar[int]
    alerts: _containers.RepeatedCompositeFieldContainer[CostAlert]
    daily_threshold_usd: str
    daily_total_usd: str
    daily_alert_triggered: bool
    monthly_threshold_usd: str
    monthly_total_usd: str
    monthly_alert_triggered: bool
    def __init__(self, alerts: _Optional[_Iterable[_Union[CostAlert, _Mapping]]] = ..., daily_threshold_usd: _Optional[str] = ..., daily_total_usd: _Optional[str] = ..., daily_alert_triggered: bool = ..., monthly_threshold_usd: _Optional[str] = ..., monthly_total_usd: _Optional[str] = ..., monthly_alert_triggered: bool = ...) -> None: ...

class ThresholdConfigRequest(_message.Message):
    __slots__ = ("daily_threshold_usd", "monthly_threshold_usd")
    DAILY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    daily_threshold_usd: float
    monthly_threshold_usd: float
    def __init__(self, daily_threshold_usd: _Optional[float] = ..., monthly_threshold_usd: _Optional[float] = ...) -> None: ...
