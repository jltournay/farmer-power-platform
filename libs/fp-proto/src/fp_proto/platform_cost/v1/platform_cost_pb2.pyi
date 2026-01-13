from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CostTypeBreakdown(_message.Message):
    __slots__ = ("cost_type", "total_cost_usd", "total_quantity", "request_count", "percentage")
    COST_TYPE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    TOTAL_QUANTITY_FIELD_NUMBER: _ClassVar[int]
    REQUEST_COUNT_FIELD_NUMBER: _ClassVar[int]
    PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    cost_type: str
    total_cost_usd: str
    total_quantity: int
    request_count: int
    percentage: float
    def __init__(self, cost_type: _Optional[str] = ..., total_cost_usd: _Optional[str] = ..., total_quantity: _Optional[int] = ..., request_count: _Optional[int] = ..., percentage: _Optional[float] = ...) -> None: ...

class DailyCostEntry(_message.Message):
    __slots__ = ("date", "total_cost_usd", "llm_cost_usd", "document_cost_usd", "embedding_cost_usd", "sms_cost_usd")
    DATE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    LLM_COST_USD_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_COST_USD_FIELD_NUMBER: _ClassVar[int]
    EMBEDDING_COST_USD_FIELD_NUMBER: _ClassVar[int]
    SMS_COST_USD_FIELD_NUMBER: _ClassVar[int]
    date: str
    total_cost_usd: str
    llm_cost_usd: str
    document_cost_usd: str
    embedding_cost_usd: str
    sms_cost_usd: str
    def __init__(self, date: _Optional[str] = ..., total_cost_usd: _Optional[str] = ..., llm_cost_usd: _Optional[str] = ..., document_cost_usd: _Optional[str] = ..., embedding_cost_usd: _Optional[str] = ..., sms_cost_usd: _Optional[str] = ...) -> None: ...

class CostSummaryRequest(_message.Message):
    __slots__ = ("start_date", "end_date", "factory_id")
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    FACTORY_ID_FIELD_NUMBER: _ClassVar[int]
    start_date: str
    end_date: str
    factory_id: str
    def __init__(self, start_date: _Optional[str] = ..., end_date: _Optional[str] = ..., factory_id: _Optional[str] = ...) -> None: ...

class CostSummaryResponse(_message.Message):
    __slots__ = ("total_cost_usd", "by_type", "period_start", "period_end", "total_requests")
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    BY_TYPE_FIELD_NUMBER: _ClassVar[int]
    PERIOD_START_FIELD_NUMBER: _ClassVar[int]
    PERIOD_END_FIELD_NUMBER: _ClassVar[int]
    TOTAL_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    total_cost_usd: str
    by_type: _containers.RepeatedCompositeFieldContainer[CostTypeBreakdown]
    period_start: str
    period_end: str
    total_requests: int
    def __init__(self, total_cost_usd: _Optional[str] = ..., by_type: _Optional[_Iterable[_Union[CostTypeBreakdown, _Mapping]]] = ..., period_start: _Optional[str] = ..., period_end: _Optional[str] = ..., total_requests: _Optional[int] = ...) -> None: ...

class DailyCostTrendRequest(_message.Message):
    __slots__ = ("start_date", "end_date", "days")
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    DAYS_FIELD_NUMBER: _ClassVar[int]
    start_date: str
    end_date: str
    days: int
    def __init__(self, start_date: _Optional[str] = ..., end_date: _Optional[str] = ..., days: _Optional[int] = ...) -> None: ...

class DailyCostTrendResponse(_message.Message):
    __slots__ = ("entries", "data_available_from")
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    DATA_AVAILABLE_FROM_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[DailyCostEntry]
    data_available_from: str
    def __init__(self, entries: _Optional[_Iterable[_Union[DailyCostEntry, _Mapping]]] = ..., data_available_from: _Optional[str] = ...) -> None: ...

class CurrentDayCostRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class CurrentDayCostResponse(_message.Message):
    __slots__ = ("date", "total_cost_usd", "by_type", "updated_at")
    class ByTypeEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DATE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    BY_TYPE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    date: str
    total_cost_usd: str
    by_type: _containers.ScalarMap[str, str]
    updated_at: str
    def __init__(self, date: _Optional[str] = ..., total_cost_usd: _Optional[str] = ..., by_type: _Optional[_Mapping[str, str]] = ..., updated_at: _Optional[str] = ...) -> None: ...

class LlmCostByAgentTypeRequest(_message.Message):
    __slots__ = ("start_date", "end_date")
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    start_date: str
    end_date: str
    def __init__(self, start_date: _Optional[str] = ..., end_date: _Optional[str] = ...) -> None: ...

class AgentTypeCost(_message.Message):
    __slots__ = ("agent_type", "cost_usd", "request_count", "tokens_in", "tokens_out", "percentage")
    AGENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    COST_USD_FIELD_NUMBER: _ClassVar[int]
    REQUEST_COUNT_FIELD_NUMBER: _ClassVar[int]
    TOKENS_IN_FIELD_NUMBER: _ClassVar[int]
    TOKENS_OUT_FIELD_NUMBER: _ClassVar[int]
    PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    agent_type: str
    cost_usd: str
    request_count: int
    tokens_in: int
    tokens_out: int
    percentage: float
    def __init__(self, agent_type: _Optional[str] = ..., cost_usd: _Optional[str] = ..., request_count: _Optional[int] = ..., tokens_in: _Optional[int] = ..., tokens_out: _Optional[int] = ..., percentage: _Optional[float] = ...) -> None: ...

class LlmCostByAgentTypeResponse(_message.Message):
    __slots__ = ("agent_costs", "total_llm_cost_usd", "period_start", "period_end")
    AGENT_COSTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_LLM_COST_USD_FIELD_NUMBER: _ClassVar[int]
    PERIOD_START_FIELD_NUMBER: _ClassVar[int]
    PERIOD_END_FIELD_NUMBER: _ClassVar[int]
    agent_costs: _containers.RepeatedCompositeFieldContainer[AgentTypeCost]
    total_llm_cost_usd: str
    period_start: str
    period_end: str
    def __init__(self, agent_costs: _Optional[_Iterable[_Union[AgentTypeCost, _Mapping]]] = ..., total_llm_cost_usd: _Optional[str] = ..., period_start: _Optional[str] = ..., period_end: _Optional[str] = ...) -> None: ...

class LlmCostByModelRequest(_message.Message):
    __slots__ = ("start_date", "end_date")
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    start_date: str
    end_date: str
    def __init__(self, start_date: _Optional[str] = ..., end_date: _Optional[str] = ...) -> None: ...

class ModelCost(_message.Message):
    __slots__ = ("model", "cost_usd", "request_count", "tokens_in", "tokens_out", "percentage")
    MODEL_FIELD_NUMBER: _ClassVar[int]
    COST_USD_FIELD_NUMBER: _ClassVar[int]
    REQUEST_COUNT_FIELD_NUMBER: _ClassVar[int]
    TOKENS_IN_FIELD_NUMBER: _ClassVar[int]
    TOKENS_OUT_FIELD_NUMBER: _ClassVar[int]
    PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    model: str
    cost_usd: str
    request_count: int
    tokens_in: int
    tokens_out: int
    percentage: float
    def __init__(self, model: _Optional[str] = ..., cost_usd: _Optional[str] = ..., request_count: _Optional[int] = ..., tokens_in: _Optional[int] = ..., tokens_out: _Optional[int] = ..., percentage: _Optional[float] = ...) -> None: ...

class LlmCostByModelResponse(_message.Message):
    __slots__ = ("model_costs", "total_llm_cost_usd", "period_start", "period_end")
    MODEL_COSTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_LLM_COST_USD_FIELD_NUMBER: _ClassVar[int]
    PERIOD_START_FIELD_NUMBER: _ClassVar[int]
    PERIOD_END_FIELD_NUMBER: _ClassVar[int]
    model_costs: _containers.RepeatedCompositeFieldContainer[ModelCost]
    total_llm_cost_usd: str
    period_start: str
    period_end: str
    def __init__(self, model_costs: _Optional[_Iterable[_Union[ModelCost, _Mapping]]] = ..., total_llm_cost_usd: _Optional[str] = ..., period_start: _Optional[str] = ..., period_end: _Optional[str] = ...) -> None: ...

class DocumentCostSummaryRequest(_message.Message):
    __slots__ = ("start_date", "end_date")
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    start_date: str
    end_date: str
    def __init__(self, start_date: _Optional[str] = ..., end_date: _Optional[str] = ...) -> None: ...

class DocumentCostSummaryResponse(_message.Message):
    __slots__ = ("total_cost_usd", "total_pages", "avg_cost_per_page_usd", "document_count", "period_start", "period_end")
    TOTAL_COST_USD_FIELD_NUMBER: _ClassVar[int]
    TOTAL_PAGES_FIELD_NUMBER: _ClassVar[int]
    AVG_COST_PER_PAGE_USD_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    PERIOD_START_FIELD_NUMBER: _ClassVar[int]
    PERIOD_END_FIELD_NUMBER: _ClassVar[int]
    total_cost_usd: str
    total_pages: int
    avg_cost_per_page_usd: str
    document_count: int
    period_start: str
    period_end: str
    def __init__(self, total_cost_usd: _Optional[str] = ..., total_pages: _Optional[int] = ..., avg_cost_per_page_usd: _Optional[str] = ..., document_count: _Optional[int] = ..., period_start: _Optional[str] = ..., period_end: _Optional[str] = ...) -> None: ...

class EmbeddingCostByDomainRequest(_message.Message):
    __slots__ = ("start_date", "end_date")
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    start_date: str
    end_date: str
    def __init__(self, start_date: _Optional[str] = ..., end_date: _Optional[str] = ...) -> None: ...

class DomainCost(_message.Message):
    __slots__ = ("knowledge_domain", "cost_usd", "tokens_total", "texts_count", "percentage")
    KNOWLEDGE_DOMAIN_FIELD_NUMBER: _ClassVar[int]
    COST_USD_FIELD_NUMBER: _ClassVar[int]
    TOKENS_TOTAL_FIELD_NUMBER: _ClassVar[int]
    TEXTS_COUNT_FIELD_NUMBER: _ClassVar[int]
    PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    knowledge_domain: str
    cost_usd: str
    tokens_total: int
    texts_count: int
    percentage: float
    def __init__(self, knowledge_domain: _Optional[str] = ..., cost_usd: _Optional[str] = ..., tokens_total: _Optional[int] = ..., texts_count: _Optional[int] = ..., percentage: _Optional[float] = ...) -> None: ...

class EmbeddingCostByDomainResponse(_message.Message):
    __slots__ = ("domain_costs", "total_embedding_cost_usd", "period_start", "period_end")
    DOMAIN_COSTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_EMBEDDING_COST_USD_FIELD_NUMBER: _ClassVar[int]
    PERIOD_START_FIELD_NUMBER: _ClassVar[int]
    PERIOD_END_FIELD_NUMBER: _ClassVar[int]
    domain_costs: _containers.RepeatedCompositeFieldContainer[DomainCost]
    total_embedding_cost_usd: str
    period_start: str
    period_end: str
    def __init__(self, domain_costs: _Optional[_Iterable[_Union[DomainCost, _Mapping]]] = ..., total_embedding_cost_usd: _Optional[str] = ..., period_start: _Optional[str] = ..., period_end: _Optional[str] = ...) -> None: ...

class BudgetStatusRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class BudgetStatusResponse(_message.Message):
    __slots__ = ("daily_threshold_usd", "daily_total_usd", "daily_alert_triggered", "daily_remaining_usd", "daily_utilization_percent", "monthly_threshold_usd", "monthly_total_usd", "monthly_alert_triggered", "monthly_remaining_usd", "monthly_utilization_percent", "by_type", "current_day", "current_month")
    class ByTypeEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DAILY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    DAILY_TOTAL_USD_FIELD_NUMBER: _ClassVar[int]
    DAILY_ALERT_TRIGGERED_FIELD_NUMBER: _ClassVar[int]
    DAILY_REMAINING_USD_FIELD_NUMBER: _ClassVar[int]
    DAILY_UTILIZATION_PERCENT_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_TOTAL_USD_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_ALERT_TRIGGERED_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_REMAINING_USD_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_UTILIZATION_PERCENT_FIELD_NUMBER: _ClassVar[int]
    BY_TYPE_FIELD_NUMBER: _ClassVar[int]
    CURRENT_DAY_FIELD_NUMBER: _ClassVar[int]
    CURRENT_MONTH_FIELD_NUMBER: _ClassVar[int]
    daily_threshold_usd: str
    daily_total_usd: str
    daily_alert_triggered: bool
    daily_remaining_usd: str
    daily_utilization_percent: float
    monthly_threshold_usd: str
    monthly_total_usd: str
    monthly_alert_triggered: bool
    monthly_remaining_usd: str
    monthly_utilization_percent: float
    by_type: _containers.ScalarMap[str, str]
    current_day: str
    current_month: str
    def __init__(self, daily_threshold_usd: _Optional[str] = ..., daily_total_usd: _Optional[str] = ..., daily_alert_triggered: bool = ..., daily_remaining_usd: _Optional[str] = ..., daily_utilization_percent: _Optional[float] = ..., monthly_threshold_usd: _Optional[str] = ..., monthly_total_usd: _Optional[str] = ..., monthly_alert_triggered: bool = ..., monthly_remaining_usd: _Optional[str] = ..., monthly_utilization_percent: _Optional[float] = ..., by_type: _Optional[_Mapping[str, str]] = ..., current_day: _Optional[str] = ..., current_month: _Optional[str] = ...) -> None: ...

class ConfigureBudgetThresholdRequest(_message.Message):
    __slots__ = ("daily_threshold_usd", "monthly_threshold_usd")
    DAILY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    daily_threshold_usd: str
    monthly_threshold_usd: str
    def __init__(self, daily_threshold_usd: _Optional[str] = ..., monthly_threshold_usd: _Optional[str] = ...) -> None: ...

class ConfigureBudgetThresholdResponse(_message.Message):
    __slots__ = ("daily_threshold_usd", "monthly_threshold_usd", "message", "updated_at")
    DAILY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_THRESHOLD_USD_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    daily_threshold_usd: str
    monthly_threshold_usd: str
    message: str
    updated_at: str
    def __init__(self, daily_threshold_usd: _Optional[str] = ..., monthly_threshold_usd: _Optional[str] = ..., message: _Optional[str] = ..., updated_at: _Optional[str] = ...) -> None: ...
