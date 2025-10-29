from unittest.mock import MagicMock, patch

from django.db import DatabaseError, OperationalError

from metrics_utility.automation_controller_billing.helpers import (
    datetime_hook,
    get_controller_version_from_db,
    get_last_entries_from_db,
    get_license_info_from_db,
)


class TestGetLicenseInfoFromDb:
    """Test cases for get_license_info_from_db function"""

    @patch('metrics_utility.automation_controller_billing.helpers.connection')
    def test_successful_license_retrieval(self, mock_connection):
        """Test successful license information retrieval"""
        # Setup
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ('LICENSE_TYPE', 'enterprise'),
            ('SUBSCRIPTION_NAME', 'Red Hat Ansible Automation Platform'),
            ('SKU', 'MCT3718'),
            ('INSTALL_UUID', '12345-67890'),
        ]

        # Execute
        result = get_license_info_from_db()

        # Assert
        expected = {
            'license_type': 'enterprise',
            'subscription_name': 'Red Hat Ansible Automation Platform',
            'sku': 'MCT3718',
            'install_uuid': '12345-67890',
        }
        assert result == expected
        mock_cursor.execute.assert_called_once()

    @patch('metrics_utility.automation_controller_billing.helpers.connection')
    def test_empty_database_result(self, mock_connection):
        """Test when database returns no license information"""
        # Setup
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        # Execute
        result = get_license_info_from_db()

        # Assert
        assert result == {}


class TestGetControllerVersionFromDb:
    """Test cases for get_controller_version_from_db function"""

    @patch('metrics_utility.automation_controller_billing.helpers.connection')
    def test_version_from_conf_setting(self, mock_connection):
        """Test successful version retrieval from conf_setting table"""
        # Setup
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [('24.6.123',), None]  # First query succeeds

        # Execute
        result = get_controller_version_from_db()

        # Assert
        assert result == '24.6.123'
        assert mock_cursor.execute.call_count == 1  # Only first query needed

    @patch('metrics_utility.automation_controller_billing.helpers.connection')
    def test_version_from_main_instance_fallback(self, mock_connection):
        """Test fallback to main_instance table when conf_setting is empty"""
        # Setup
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [None, ('24.5.0',)]  # First fails, second succeeds

        # Execute
        result = get_controller_version_from_db()

        # Assert
        assert result == '24.5.0'
        assert mock_cursor.execute.call_count == 2  # Both queries executed

    @patch('metrics_utility.automation_controller_billing.helpers.connection')
    def test_no_version_found(self, mock_connection):
        """Test when no version is found in either table"""
        # Setup
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        # Execute
        result = get_controller_version_from_db()

        # Assert
        assert result == 'No data found'
        assert mock_cursor.execute.call_count == 2  # Both queries attempted

    @patch('metrics_utility.automation_controller_billing.helpers.logger')
    @patch('metrics_utility.automation_controller_billing.helpers.connection')
    def test_database_error_returns_error_message(self, mock_connection, mock_logger):
        """Test error handling returns 'Database error' when database fails"""
        # Setup
        mock_connection.cursor.side_effect = OperationalError('Database unavailable')

        # Execute
        result = get_controller_version_from_db()

        # Assert
        assert result == 'Database error'
        assert mock_logger.error.call_count == 2  # Two error logs: original error + fallback message
        # Check both error messages were logged
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        assert any('Error getting AWX/Controller version from database' in call for call in error_calls)
        assert any('Returning "Database error" as fallback' in call for call in error_calls)

    @patch('metrics_utility.automation_controller_billing.helpers.connection')
    def test_version_priority_order(self, mock_connection):
        """Test that the SQL query includes proper ORDER BY for version priority"""
        # Setup
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ('24.6.0',)

        # Execute
        get_controller_version_from_db()

        # Assert - Check that the SQL query has correct ORDER BY structure
        sql_call = mock_cursor.execute.call_args_list[0][0][0]
        assert 'ORDER BY' in sql_call
        assert 'CASE key' in sql_call
        assert 'AWX_VERSION' in sql_call
        assert 'TOWER_VERSION' in sql_call


class TestGetLastEntriesFromDb:
    """Test cases for get_last_entries_from_db function"""

    @patch('metrics_utility.automation_controller_billing.helpers.connection')
    def test_successful_entries_retrieval(self, mock_connection):
        """Test successful last entries retrieval"""
        # Setup
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        test_json = '{"config": "2024-01-01T00:00:00Z", "jobs": "2024-01-02T00:00:00Z", "hosts": "2024-01-03T00:00:00Z"}'
        mock_cursor.fetchone.return_value = (test_json,)

        # Execute
        result = get_last_entries_from_db()

        # Assert
        assert result == test_json
        mock_cursor.execute.assert_called_once()
        # Verify correct SQL query
        sql_call = mock_cursor.execute.call_args[0][0]
        assert 'AUTOMATION_ANALYTICS_LAST_ENTRIES' in sql_call

    @patch('metrics_utility.automation_controller_billing.helpers.connection')
    def test_no_entries_or_empty_value(self, mock_connection):
        """Test when no entries found or value is empty"""
        # Setup
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # Could be no row or (None,)

        # Execute
        result = get_last_entries_from_db()

        # Assert
        assert result is None

    @patch('metrics_utility.automation_controller_billing.helpers.logger')
    @patch('metrics_utility.automation_controller_billing.helpers.connection')
    def test_database_error_handling(self, mock_connection, mock_logger):
        """Test error handling when database query fails"""
        # Setup
        mock_connection.cursor.side_effect = DatabaseError('Query failed')

        # Execute
        result = get_last_entries_from_db()

        # Assert
        assert result is None
        mock_logger.error.assert_called_once()
        assert 'Error getting AUTOMATION_ANALYTICS_LAST_ENTRIES from database' in str(mock_logger.error.call_args)


class TestDatetimeHook:
    """Test cases for datetime_hook function"""

    def test_empty_dict_handling(self):
        """Test handling of empty dictionary"""
        # Execute
        result = datetime_hook({})

        # Assert
        assert result == {}

    def test_multiple_datetime_fields(self):
        """Test parsing multiple collector timestamps in one dict"""
        # Setup - realistic collector function names with timestamps
        test_data = {
            'config': '2024-01-01T10:00:00Z',
            'jobs': '2024-01-02T15:30:00Z',
            'hosts': '2024-01-03T08:45:00Z',
        }

        # Execute
        result = datetime_hook(test_data)

        # Assert
        assert 'config' in result
        assert 'jobs' in result
        assert 'hosts' in result
        # All collector timestamps should be parsed
        assert str(result['config']).startswith('2024-01-01')
        assert str(result['jobs']).startswith('2024-01-02')
        assert str(result['hosts']).startswith('2024-01-03')


class TestIntegration:
    """Integration tests for helper functions working together"""

    @patch('metrics_utility.automation_controller_billing.helpers.connection')
    def test_functions_work_with_real_data(self, mock_connection):
        """Test that all helper functions work with realistic data"""
        # Setup realistic database responses
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        # Setup data for all function calls in sequence:
        # 1. get_license_info_from_db() - fetchall()
        # 2. get_controller_version_from_db() - fetchone()
        # 3. get_last_entries_from_db() - fetchone()
        mock_cursor.fetchall.return_value = [
            ('LICENSE_TYPE', 'enterprise'),
            ('SUBSCRIPTION_NAME', 'Red Hat AAP'),
        ]
        mock_cursor.fetchone.side_effect = [
            ('24.6.0',),  # Version query result
            ('{"config": "2024-01-01T00:00:00Z", "jobs": "2024-01-02T00:00:00Z"}',),  # Last entries result
        ]

        # Execute all functions
        license_info = get_license_info_from_db()
        version = get_controller_version_from_db()
        entries = get_last_entries_from_db()

        # Assert all return expected realistic data
        assert license_info == {
            'license_type': 'enterprise',
            'subscription_name': 'Red Hat AAP',
        }
        assert version == '24.6.0'
        assert entries == '{"config": "2024-01-01T00:00:00Z", "jobs": "2024-01-02T00:00:00Z"}'
