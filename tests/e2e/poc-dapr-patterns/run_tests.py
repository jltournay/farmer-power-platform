#!/usr/bin/env python3
"""
PoC Test Runner: Validates DAPR Patterns (ADR-010, ADR-011)

This script tests:
1. gRPC service invocation via DAPR proxy (Service A <-> Service B)
2. Streaming pub/sub with subscribe_with_handler()
3. Retry behavior on transient failures
4. Dead letter queue (DLQ) for permanent failures

Prerequisites:
    cd tests/e2e/poc-dapr-patterns
    docker compose up --build -d
    # Wait for services to be healthy
    python run_tests.py

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --test grpc  # Run only gRPC tests
    python run_tests.py --test pubsub # Run only pub/sub tests
    python run_tests.py --test dlq   # Run only DLQ tests
"""

import argparse
import subprocess
import sys
import time
import uuid

import grpc
import requests

# Generate proto stubs for local testing
# python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/poc.proto

SERVICE_A_HTTP = "http://localhost:8001"
SERVICE_B_HTTP = "http://localhost:8002"
SERVICE_A_GRPC = "localhost:50061"
SERVICE_B_GRPC = "localhost:50062"
DAPR_A_GRPC = "localhost:50001"  # Not exposed, but for reference

# Test results
results = []


def log_test(name: str, passed: bool, details: str = ""):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"       {details}")
    results.append({"name": name, "passed": passed, "details": details})


def wait_for_services(timeout: int = 60):
    """Wait for all services to be healthy."""
    print("\n🔄 Waiting for services to be healthy...")
    start = time.time()

    while time.time() - start < timeout:
        try:
            resp_a = requests.get(f"{SERVICE_A_HTTP}/ready", timeout=2)
            resp_b = requests.get(f"{SERVICE_B_HTTP}/ready", timeout=2)

            if resp_a.status_code == 200 and resp_b.status_code == 200:
                data_a = resp_a.json()
                data_b = resp_b.json()

                if data_a.get("subscription_ready") and data_b.get("subscription_ready"):
                    print("✅ All services healthy and subscriptions ready")
                    return True

        except requests.exceptions.ConnectionError:
            pass

        time.sleep(2)

    print("❌ Services did not become healthy in time")
    return False


def clear_messages():
    """Clear all received messages in both services."""
    try:
        requests.post(f"{SERVICE_A_HTTP}/clear-messages", timeout=5)
        requests.post(f"{SERVICE_B_HTTP}/clear-messages", timeout=5)
    except Exception as e:
        print(f"Warning: Could not clear messages: {e}")


# =============================================================================
# Test 1: gRPC Service Invocation via DAPR
# =============================================================================


def test_grpc_service_a_echo():
    """Test calling Service A's EchoService directly (without DAPR)."""
    try:
        # Import generated proto (requires running protoc first)
        sys.path.insert(0, ".")
        import poc_pb2
        import poc_pb2_grpc

        channel = grpc.insecure_channel(SERVICE_A_GRPC)
        stub = poc_pb2_grpc.EchoServiceStub(channel)

        request = poc_pb2.EchoRequest(message="Hello from test")
        response = stub.Echo(request, timeout=5)

        passed = response.message == "Hello from test" and response.service == "service-a"
        log_test(
            "gRPC: Service A Echo (direct)",
            passed,
            f"Response: {response.message}, service: {response.service}",
        )
        return passed

    except Exception as e:
        log_test("gRPC: Service A Echo (direct)", False, str(e))
        return False


def test_grpc_service_b_calculator():
    """Test calling Service B's CalculatorService directly (without DAPR)."""
    try:
        sys.path.insert(0, ".")
        import poc_pb2
        import poc_pb2_grpc

        channel = grpc.insecure_channel(SERVICE_B_GRPC)
        stub = poc_pb2_grpc.CalculatorServiceStub(channel)

        request = poc_pb2.AddRequest(a=5, b=3)
        response = stub.Add(request, timeout=5)

        passed = response.result == 8 and response.service == "service-b"
        log_test(
            "gRPC: Service B Calculator.Add (direct)",
            passed,
            f"5 + 3 = {response.result}, service: {response.service}",
        )
        return passed

    except Exception as e:
        log_test("gRPC: Service B Calculator.Add (direct)", False, str(e))
        return False


# =============================================================================
# Test 2: Pub/Sub Happy Path
# =============================================================================


def test_pubsub_success():
    """Test successful pub/sub message flow."""
    clear_messages()
    event_id = f"test-success-{uuid.uuid4().hex[:8]}"

    try:
        # Publish from Service B to Service A
        resp = requests.post(
            f"{SERVICE_B_HTTP}/publish-to-a",
            params={"event_type": "success", "event_id": event_id},
            timeout=10,
        )

        if resp.status_code != 200:
            log_test("Pub/Sub: Success message", False, f"Publish failed: {resp.text}")
            return False

        # Wait for message to be received
        time.sleep(3)

        # Check if Service A received the message
        resp = requests.get(f"{SERVICE_A_HTTP}/received-messages", timeout=5)
        messages = resp.json().get("messages", [])

        # Find our message
        found = any(m.get("id") == event_id and m.get("status") == "success" for m in messages)

        log_test(
            "Pub/Sub: Success message (B → A)",
            found,
            f"Event {event_id} received: {found}, total messages: {len(messages)}",
        )
        return found

    except Exception as e:
        log_test("Pub/Sub: Success message", False, str(e))
        return False


# =============================================================================
# Test 3: Pub/Sub Retry Behavior
# =============================================================================


def test_pubsub_retry():
    """Test pub/sub retry on transient failure."""
    clear_messages()
    event_id = f"test-retry-{uuid.uuid4().hex[:8]}"

    try:
        # Publish retry_once message from Service B to Service A
        resp = requests.post(
            f"{SERVICE_B_HTTP}/publish-to-a",
            params={"event_type": "retry_once", "event_id": event_id},
            timeout=10,
        )

        if resp.status_code != 200:
            log_test("Pub/Sub: Retry behavior", False, f"Publish failed: {resp.text}")
            return False

        # Wait for retry cycle (initial failure + retry delay + success)
        time.sleep(8)

        # Check if Service A eventually processed the message
        resp = requests.get(f"{SERVICE_A_HTTP}/received-messages", timeout=5)
        messages = resp.json().get("messages", [])

        # Should see both retry attempt and success
        retry_attempt = any(m.get("id") == event_id and m.get("status") == "retrying" for m in messages)
        success_after = any(m.get("id") == event_id and m.get("status") == "success_after_retry" for m in messages)

        passed = retry_attempt and success_after
        log_test(
            "Pub/Sub: Retry behavior",
            passed,
            f"Retry attempt: {retry_attempt}, Success after retry: {success_after}",
        )
        return passed

    except Exception as e:
        log_test("Pub/Sub: Retry behavior", False, str(e))
        return False


# =============================================================================
# Test 4: Dead Letter Queue
# =============================================================================


def test_pubsub_dlq():
    """Test that permanently failing messages go to DLQ."""
    clear_messages()
    event_id = f"test-dlq-{uuid.uuid4().hex[:8]}"

    try:
        # Publish always_fail message from Service B to Service A
        resp = requests.post(
            f"{SERVICE_B_HTTP}/publish-to-a",
            params={"event_type": "always_fail", "event_id": event_id},
            timeout=10,
        )

        if resp.status_code != 200:
            log_test("Pub/Sub: DLQ behavior", False, f"Publish failed: {resp.text}")
            return False

        # Wait for retries to exhaust and DLQ to receive (3 retries * 1s + processing)
        time.sleep(15)

        # Check if message appeared in DLQ (monitored by Service B)
        resp = requests.get(f"{SERVICE_B_HTTP}/dlq-messages", timeout=5)
        dlq_messages = resp.json().get("messages", [])

        # Find our message in DLQ
        found_in_dlq = any(m.get("id") == event_id for m in dlq_messages)

        log_test(
            "Pub/Sub: DLQ receives failed messages",
            found_in_dlq,
            f"Event {event_id} in DLQ: {found_in_dlq}, DLQ count: {len(dlq_messages)}",
        )
        return found_in_dlq

    except Exception as e:
        log_test("Pub/Sub: DLQ behavior", False, str(e))
        return False


# =============================================================================
# Test 5: gRPC Client Resilience (ADR-005)
# =============================================================================


def test_grpc_client_resilience():
    """Test gRPC client retry and reconnection after server restart (ADR-005).

    This test validates:
    1. Initial call to Service B succeeds
    2. Restart Service B container
    3. Call to Service B succeeds after retry (without restarting Service A)
    """
    try:
        # Step 1: Initial call should succeed
        print("  Step 1: Initial call to Service B via Service A...")
        resp = requests.get(f"{SERVICE_A_HTTP}/call-service-b?a=10&b=5", timeout=10)
        if resp.status_code != 200 or resp.json().get("status") != "success":
            log_test("gRPC: Client resilience (ADR-005)", False, f"Initial call failed: {resp.text}")
            return False

        initial_result = resp.json().get("result")
        if initial_result != 15:
            log_test("gRPC: Client resilience (ADR-005)", False, f"Wrong result: {initial_result}")
            return False

        print(f"       Initial call succeeded: 10 + 5 = {initial_result}")

        # Get initial client stats
        stats_before = requests.get(f"{SERVICE_A_HTTP}/client-stats", timeout=5).json()
        print(f"       Client stats before restart: {stats_before}")

        # Step 2: Restart Service B AND its DAPR sidecar (simulates pod restart)
        print("  Step 2: Restarting Service B + DAPR sidecar (simulates pod restart)...")
        subprocess.run(
            ["docker", "restart", "poc-service-b", "poc-service-b-dapr"],
            capture_output=True,
            timeout=60,
        )

        # Wait for Service B to be healthy again
        print("  Step 3: Waiting for Service B and DAPR to be healthy...")
        time.sleep(15)

        # Verify Service B is back and ready
        for i in range(15):
            try:
                ready_resp = requests.get(f"{SERVICE_B_HTTP}/ready", timeout=2)
                if ready_resp.status_code == 200:
                    data = ready_resp.json()
                    if data.get("subscription_ready"):
                        print("       Service B is healthy and subscriptions ready")
                        break
                    else:
                        print("       Service B healthy but subscriptions not ready yet...")
            except requests.exceptions.ConnectionError:
                print(f"       Service B not reachable yet (attempt {i+1}/15)...")
            time.sleep(2)

        # Extra wait for DAPR mesh to stabilize
        print("       Waiting for DAPR mesh to stabilize...")
        time.sleep(5)

        # Step 4: Call Service B again - should succeed after retry
        print("  Step 4: Calling Service B again (should retry and succeed)...")
        resp = requests.get(f"{SERVICE_A_HTTP}/call-service-b?a=20&b=7", timeout=30)

        if resp.status_code != 200:
            log_test("gRPC: Client resilience (ADR-005)", False, f"Call after restart failed: {resp.text}")
            return False

        data = resp.json()
        if data.get("status") != "success":
            log_test("gRPC: Client resilience (ADR-005)", False, f"Call failed: {data.get('error')}")
            return False

        result = data.get("result")
        stats_after = data.get("client_stats", {})

        if result != 27:
            log_test("gRPC: Client resilience (ADR-005)", False, f"Wrong result: {result}")
            return False

        print(f"       Call succeeded: 20 + 7 = {result}")
        print(f"       Client stats after restart: {stats_after}")

        # The retry count might have increased due to reconnection
        log_test(
            "gRPC: Client resilience (ADR-005)",
            True,
            f"Auto-reconnected after server restart. Stats: calls={stats_after.get('call_count')}, retries={stats_after.get('retry_count')}",
        )
        return True

    except Exception as e:
        log_test("gRPC: Client resilience (ADR-005)", False, str(e))
        return False


# =============================================================================
# Main
# =============================================================================


def run_all_tests(include_resilience: bool = False):
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  PoC: DAPR Patterns Validation (ADR-005, ADR-010, ADR-011)")
    print("=" * 60)

    if not wait_for_services():
        print("\n❌ Cannot run tests - services not healthy")
        sys.exit(1)

    print("\n" + "-" * 60)
    print("  Running Tests")
    print("-" * 60)

    # gRPC tests
    print("\n📡 gRPC Service Invocation Tests:")
    test_grpc_service_a_echo()
    test_grpc_service_b_calculator()

    # Pub/Sub tests
    print("\n📨 Pub/Sub Streaming Tests:")
    test_pubsub_success()
    test_pubsub_retry()
    test_pubsub_dlq()

    # Resilience tests (optional - takes longer due to container restart)
    if include_resilience:
        print("\n🔄 gRPC Client Resilience Tests (ADR-005):")
        test_grpc_client_resilience()

    # Summary
    print("\n" + "=" * 60)
    print("  Test Summary")
    print("=" * 60)

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed

    for r in results:
        status = "✅" if r["passed"] else "❌"
        print(f"  {status} {r['name']}")

    print(f"\n  Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    print("=" * 60)

    if failed > 0:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="PoC Test Runner")
    parser.add_argument(
        "--test",
        choices=["grpc", "pubsub", "dlq", "resilience", "all"],
        default="all",
        help="Which tests to run",
    )
    parser.add_argument(
        "--with-resilience",
        action="store_true",
        help="Include resilience test (restarts containers, takes longer)",
    )
    args = parser.parse_args()

    if args.test == "all":
        run_all_tests(include_resilience=args.with_resilience)
    elif args.test == "grpc":
        wait_for_services()
        test_grpc_service_a_echo()
        test_grpc_service_b_calculator()
    elif args.test == "pubsub":
        wait_for_services()
        test_pubsub_success()
        test_pubsub_retry()
    elif args.test == "dlq":
        wait_for_services()
        test_pubsub_dlq()
    elif args.test == "resilience":
        wait_for_services()
        print("\n🔄 gRPC Client Resilience Test (ADR-005):")
        test_grpc_client_resilience()
        # Print result
        if results:
            r = results[-1]
            status = "✅" if r["passed"] else "❌"
            print(f"\n{status} {r['name']}")


if __name__ == "__main__":
    main()
