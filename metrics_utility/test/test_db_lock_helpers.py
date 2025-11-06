from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, call, patch

import pytest

from metrics_utility.automation_controller_billing.collector import Collector
from metrics_utility.base.db_lock_helpers import advisory_lock


class TestCollectorLocks:
    def acquire_lock(self, thread_id, key='contention_test_lock'):
        try:
            with advisory_lock(f'{key}', wait=False) as acquired:
                if acquired:
                    lock = f'Thread {thread_id} acquired lock. Key: {key}'
                    return lock
                else:
                    lock = f'Thread {thread_id} did not, and should not, acquire lock. Key: {key}'
                    return lock
        except Exception as e:
            lock = f'Thread {thread_id} encountered error: {e}. Key: {key}'
            return lock

    @pytest.mark.parametrize(
        'lock_acquired,expected_acquired',
        [
            (False, False),  # Lock fails
            (True, True),  # Lock succeeds
        ],
    )
    @patch('metrics_utility.automation_controller_billing.collector.advisory_lock')
    def test_collector_lock_behavior(self, mock_advisory_lock, lock_acquired, expected_acquired):
        """Test that Collector._pg_advisory_lock correctly uses the advisory_lock function"""
        # Mock the advisory_lock context manager
        mock_advisory_lock.return_value.__enter__.return_value = lock_acquired
        mock_advisory_lock.return_value.__exit__.return_value = None

        collector = Collector(ship_target='directory', billing_provider_params={'ship_path': '/tmp/test'})

        # Test the _pg_advisory_lock method directly
        with collector._pg_advisory_lock('test_key', wait=False) as acquired:
            assert acquired == expected_acquired

        # Verify the advisory_lock was called with correct parameters
        mock_advisory_lock.assert_called_once_with('test_key', wait=False)

    @patch('metrics_utility.automation_controller_billing.collector.advisory_lock')
    def test_gather_calls_lock(self, mock_advisory_lock):
        """Test that Collector.gather() attempts to acquire the lock"""
        # Mock the lock to fail so gather returns early
        mock_advisory_lock.return_value.__enter__.return_value = False
        mock_advisory_lock.return_value.__exit__.return_value = None

        collector = Collector(ship_target='directory', billing_provider_params={'ship_path': '/tmp/test'})
        result = collector.gather()

        # Should return None when lock fails
        assert result is None

        # Verify the lock was attempted
        mock_advisory_lock.assert_called_with('gather_automation_controller_billing_lock', wait=False)

    @patch('metrics_utility.base.db_lock_helpers.connections')
    @patch('metrics_utility.base.db_lock_helpers.connection')
    def test_string_key_conversion(self, mock_connection, mock_connections):
        mock_connection.vendor = 'postgresql'

        # Mock the cursor and its operations
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = [True]  # Lock acquisition succeeds

        # Set up the cursor context manager properly
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_connections.__getitem__.return_value.cursor.return_value = mock_cursor_context

        with advisory_lock('my_string_key', wait=False) as acquired:
            assert acquired is True
        executed_sql = mock_cursor.execute.call_args_list[0][0][0]  # This returns the argument for the first call to execute
        assert 'SELECT pg_try_advisory_lock(' in executed_sql
        assert 'my_string_key' not in executed_sql

    @patch('metrics_utility.base.db_lock_helpers.connection')
    def test_invalid_tuple_key(self, mock_connection):
        mock_connection.vendor = 'postgresql'

        with pytest.raises(ValueError, match='Tuples and lists as lock IDs must have exactly two entries'):
            advisory_lock([1, 2, 3], wait=False).__enter__()

        with pytest.raises(ValueError, match='Both members of a tuple/list lock ID must be integers'):
            advisory_lock(['a', 'b'], wait=False).__enter__()

    @patch('metrics_utility.base.db_lock_helpers._pglocks_advisory_lock')
    @patch('metrics_utility.base.db_lock_helpers.connection')
    def test_lock_with_session_timeout_success(self, mock_connection, mock_django_pglocks_advisory_lock):
        mock_connection.vendor = 'postgresql'
        print(f'connection: {mock_connection.vendor}')
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [['300000'], ['0']]

        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_connection.cursor.return_value = mock_cursor_context

        mock_django_lock_context = MagicMock()
        mock_django_lock_context.__enter__.return_value = True
        mock_django_lock_context.__exit__.return_value = None
        mock_django_pglocks_advisory_lock.return_value = mock_django_lock_context

        with advisory_lock('test_key', lock_session_timeout_milliseconds=5000) as acquired:
            assert acquired is True

        expected_calls = [
            call('SHOW idle_in_transaction_session_timeout'),
            call('SHOW idle_session_timeout'),
            call('SET idle_in_transaction_session_timeout = %s', (5000,)),
            call('SET idle_session_timeout = %s', (5000,)),
            call('SET idle_in_transaction_session_timeout = %s', ('300000',)),
            call('SET idle_session_timeout = %s', ('0',)),
        ]
        mock_cursor.execute.assert_has_calls(expected_calls)

    @patch('metrics_utility.base.db_lock_helpers._pglocks_advisory_lock')
    def test_lock_convention_integration(self, mock_django_pglocks_advisory_lock):
        mock_django_pglocks_advisory_lock.return_value.__enter__.side_effect = [True, False, False]
        mock_django_pglocks_advisory_lock.return_value.__exit__.return_value = None

        futures = []
        with ThreadPoolExecutor() as executor:
            for i in range(3):
                future = executor.submit(self.acquire_lock, i, 'contention_test_lock')
                futures.append(future)
            results = [future.result() for future in futures]

        acquired_count = len([r for r in results if 'acquired lock' in r])
        failed_count = len([r for r in results if 'did not, and should not, acquire lock' in r])
        assert acquired_count == 1
        assert failed_count == 2

    @patch('metrics_utility.base.db_lock_helpers._pglocks_advisory_lock')
    def test_multiple_locks_convention_integration(self, mock_django_pglocks_advisory_lock):
        mock_django_pglocks_advisory_lock.return_value.__enter__.side_effect = [True, True, True]
        mock_django_pglocks_advisory_lock.return_value.__exit__.return_value = None

        futures = []
        with ThreadPoolExecutor() as executor:
            for i in range(3):
                future = executor.submit(self.acquire_lock, i, f'contention_test_lock + {i}')
                futures.append(future)
            results = [future.result() for future in futures]

        acquired_count = len([r for r in results if 'acquired lock' in r])
        failed_count = len([r for r in results if 'did not, and should not, acquire lock' in r])
        assert acquired_count == 3
        assert failed_count == 0


class TestBugFixes:
    """Tests specifically for bugs found in PR review"""

    def test_key_generation_no_unbound_local_error(self):
        """Test that _validate_and_create_generated_key handles all key types without UnboundLocalError"""
        from metrics_utility.base.db_lock_helpers import _validate_and_create_generated_key

        # Test all supported key types - these should not raise UnboundLocalError
        test_cases = [
            'string_key',  # String key
            42,  # Positive integer
            -42,  # Negative integer
            [1, 2],  # Valid list
            (3, 4),  # Valid tuple
        ]

        for key in test_cases:
            try:
                result = _validate_and_create_generated_key(key)
                assert isinstance(result, int), f'Key {key} should return an integer, got {type(result)}'
                assert result >= 0, f'Key {key} should return non-negative integer, got {result}'
            except UnboundLocalError:
                pytest.fail(f'UnboundLocalError raised for key type {type(key).__name__}: {key}')
            except Exception:
                # Other exceptions are fine (like ValueError for invalid keys)
                pass

    def test_deterministic_key_generation(self):
        """Test that key generation is deterministic across multiple calls"""
        from metrics_utility.base.db_lock_helpers import _validate_and_create_generated_key

        test_keys = ['test_string', 123, [1, 2], (5, 10)]

        for key in test_keys:
            # Generate the same key multiple times
            results = []
            for _ in range(5):
                try:
                    result = _validate_and_create_generated_key(key)
                    results.append(result)
                except Exception:
                    # Skip invalid keys
                    break

            if results:
                # All results should be identical (deterministic)
                assert all(r == results[0] for r in results), f'Key {key} produced non-deterministic results: {results}'

    @patch('metrics_utility.base.db_lock_helpers.connection')
    def test_exception_propagation_from_user_code(self, mock_connection):
        """Test that exceptions from user code properly propagate through advisory_lock"""
        mock_connection.vendor = 'postgresql'

        class CustomException(Exception):
            pass

        # Mock successful lock acquisition
        with patch('metrics_utility.base.db_lock_helpers._pglocks_advisory_lock') as mock_lock:
            mock_lock.return_value.__enter__.return_value = True
            mock_lock.return_value.__exit__.return_value = None

            # Test that user exceptions propagate properly
            with pytest.raises(CustomException):
                with advisory_lock('test_key', wait=False):
                    raise CustomException('User code error')

    @patch('metrics_utility.base.db_lock_helpers.connection')
    def test_timeout_restoration_on_exception(self, mock_connection):
        """Test that timeout settings are restored even when exceptions occur in user code"""
        mock_connection.vendor = 'postgresql'

        # Mock cursor operations
        mock_cursor = MagicMock()
        mock_cursor.execute.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [['300000'], ['0']]  # Original timeout values

        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_connection.cursor.return_value = mock_cursor_context

        # Mock successful lock acquisition
        with patch('metrics_utility.base.db_lock_helpers._pglocks_advisory_lock') as mock_lock:
            mock_lock.return_value.__enter__.return_value = True
            mock_lock.return_value.__exit__.return_value = None

            # Test that timeout restoration happens even when user code raises exception
            with pytest.raises(RuntimeError):
                with advisory_lock('test_key', lock_session_timeout_milliseconds=5000):
                    raise RuntimeError('Simulated user error')

            # Verify timeout restoration calls were made
            expected_calls = [
                call('SHOW idle_in_transaction_session_timeout'),
                call('SHOW idle_session_timeout'),
                call('SET idle_in_transaction_session_timeout = %s', (5000,)),
                call('SET idle_session_timeout = %s', (5000,)),
                # These restoration calls should happen in finally block
                call('SET idle_in_transaction_session_timeout = %s', ('300000',)),
                call('SET idle_session_timeout = %s', ('0',)),
            ]
            mock_cursor.execute.assert_has_calls(expected_calls)

    @patch('metrics_utility.base.db_lock_helpers.connection')
    def test_timeout_restoration_failure_is_logged(self, mock_connection):
        """Test that failures in timeout restoration are logged but don't raise exceptions"""
        mock_connection.vendor = 'postgresql'

        # Mock cursor that fails on restoration
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = [
            mock_cursor,  # SHOW idle_in_transaction_session_timeout
            mock_cursor,  # SHOW idle_session_timeout
            None,  # SET idle_in_transaction_session_timeout (setup)
            None,  # SET idle_session_timeout (setup)
            Exception('Database connection lost'),  # SET idle_in_transaction_session_timeout (restore)
        ]
        mock_cursor.fetchone.side_effect = [['300000'], ['0']]

        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_connection.cursor.return_value = mock_cursor_context

        # Mock successful lock acquisition
        with patch('metrics_utility.base.db_lock_helpers._pglocks_advisory_lock') as mock_lock:
            mock_lock.return_value.__enter__.return_value = True
            mock_lock.return_value.__exit__.return_value = None

            # Mock logger to verify error is logged
            with patch('metrics_utility.base.db_lock_helpers.logger') as mock_logger:
                # This should complete successfully despite restoration failure
                advisory_lock('test_key', lock_session_timeout_milliseconds=5000).__enter__()

                # Verify error was logged
                mock_logger.error.assert_called_once()
                error_message = mock_logger.error.call_args[0][0]
                assert 'Error restoring timeout values: Database connection lost' in error_message
