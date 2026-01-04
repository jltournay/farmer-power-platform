"""Unit tests for AI Model OpenTelemetry tracing."""

from unittest.mock import MagicMock, patch


class TestTracingSetup:
    """Tests for tracing setup functions."""

    def test_setup_tracing_disabled_does_nothing(self) -> None:
        """setup_tracing should do nothing when otel_enabled=False."""
        with patch("ai_model.infrastructure.tracing.settings") as mock_settings:
            mock_settings.otel_enabled = False

            from ai_model.infrastructure.tracing import setup_tracing

            # Should not raise and should return early
            setup_tracing()

    def test_setup_tracing_enabled_configures_provider(self) -> None:
        """setup_tracing should configure TracerProvider when enabled."""
        with (
            patch("ai_model.infrastructure.tracing.settings") as mock_settings,
            patch("ai_model.infrastructure.tracing.TracerProvider") as mock_provider_class,
            patch("ai_model.infrastructure.tracing.OTLPSpanExporter") as mock_exporter_class,
            patch("ai_model.infrastructure.tracing.BatchSpanProcessor") as mock_processor_class,
            patch("ai_model.infrastructure.tracing.trace") as mock_trace,
            patch("ai_model.infrastructure.tracing._instrument_libraries") as mock_instrument,
        ):
            mock_settings.otel_enabled = True
            mock_settings.service_name = "ai-model"
            mock_settings.service_version = "0.1.0"
            mock_settings.otel_service_namespace = "farmer-power"
            mock_settings.environment = "test"
            mock_settings.otel_exporter_endpoint = "http://localhost:4317"
            mock_settings.otel_exporter_insecure = True

            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            from ai_model.infrastructure.tracing import setup_tracing

            setup_tracing()

            mock_provider_class.assert_called_once()
            mock_exporter_class.assert_called_once()
            mock_processor_class.assert_called_once()
            mock_trace.set_tracer_provider.assert_called_once_with(mock_provider)
            mock_instrument.assert_called_once()

    def test_instrument_fastapi_disabled_does_nothing(self) -> None:
        """instrument_fastapi should do nothing when otel_enabled=False."""
        with patch("ai_model.infrastructure.tracing.settings") as mock_settings:
            mock_settings.otel_enabled = False

            from ai_model.infrastructure.tracing import instrument_fastapi

            mock_app = MagicMock()
            # Should not raise and should return early
            instrument_fastapi(mock_app)

    def test_instrument_fastapi_enabled_instruments_app(self) -> None:
        """instrument_fastapi should instrument the app when enabled."""
        with (
            patch("ai_model.infrastructure.tracing.settings") as mock_settings,
            patch("ai_model.infrastructure.tracing.FastAPIInstrumentor") as mock_instrumentor,
        ):
            mock_settings.otel_enabled = True

            from ai_model.infrastructure.tracing import instrument_fastapi

            mock_app = MagicMock()
            instrument_fastapi(mock_app)

            mock_instrumentor.instrument_app.assert_called_once_with(
                mock_app,
                excluded_urls="health,ready,metrics",
            )

    def test_shutdown_tracing_disabled_does_nothing(self) -> None:
        """shutdown_tracing should do nothing when otel_enabled=False."""
        with patch("ai_model.infrastructure.tracing.settings") as mock_settings:
            mock_settings.otel_enabled = False

            from ai_model.infrastructure.tracing import shutdown_tracing

            # Should not raise and should return early
            shutdown_tracing()

    def test_shutdown_tracing_enabled_shuts_down_provider(self) -> None:
        """shutdown_tracing should shutdown provider when enabled."""
        with (
            patch("ai_model.infrastructure.tracing.settings") as mock_settings,
            patch("ai_model.infrastructure.tracing.trace") as mock_trace,
        ):
            mock_settings.otel_enabled = True

            mock_provider = MagicMock()
            mock_trace.get_tracer_provider.return_value = mock_provider

            from ai_model.infrastructure.tracing import shutdown_tracing

            shutdown_tracing()

            mock_provider.shutdown.assert_called_once()

    def test_get_tracer_returns_tracer(self) -> None:
        """get_tracer should return a tracer for the given name."""
        with patch("ai_model.infrastructure.tracing.trace") as mock_trace:
            mock_tracer = MagicMock()
            mock_trace.get_tracer.return_value = mock_tracer

            from ai_model.infrastructure.tracing import get_tracer

            result = get_tracer("test.module")

            mock_trace.get_tracer.assert_called_once_with("test.module")
            assert result is mock_tracer
