import os

import pytest

from openpyxl import load_workbook
from pandas import read_excel

from metrics_utility import prepare
from metrics_utility.test.util import run_build_int


prepare()

env_vars = {
    'METRICS_UTILITY_SHIP_PATH': './metrics_utility/test/test_data',
    'METRICS_UTILITY_SHIP_TARGET': 'directory',
    'METRICS_UTILITY_REPORT_TYPE': 'CCSPv2',
    'METRICS_UTILITY_OPTIONAL_CCSP_REPORT_SHEETS': 'ccsp_summary,managed_nodes,indirectly_managed_nodes,usage_by_organizations',
}
file_path = './metrics_utility/test/test_data/reports/2025/02/CCSPv2-2025-02-25--2025-02-26.xlsx'


def test_uses_since_and_until_values():
    env_vars['METRICS_UTILITY_REPORT_TYPE'] = 'CCSPv2'
    args = {'since': '2025-02-25', 'until': '2025-02-26', 'force': True}
    run_build_int(env_vars, args)
    try:
        workbook = load_workbook(filename=file_path)
        worksheet = read_excel(file_path, sheet_name='Usage Reporting')
        cell_value = worksheet.iat[3, 1]

        assert cell_value == '2025-02-25, 2025-02-26', f"Expected '2025-02-25, 2025-02-26' but got '{cell_value}'"
    finally:
        workbook.close()
        os.remove(file_path)


month_file_path = './metrics_utility/test/test_data/reports/2025/04/CCSPv2-2025-04.xlsx'


def test_accepts_month_and_ignores_since_until(caplog):
    handle_build_exception(
        env_vars,
        {'since': '2024-01-01', 'until': '2024-02-01', 'month': '2025-04', 'force': True},
        'The --since and --until parameters are not allowed if the --month parameter is provided.',
        caplog,
    )


def test_renewal_guidance_fails_with_until_params(caplog):
    command_args = [
        {'args': {'until': '2025-01-01'}, 'report_type': 'RENEWAL_GUIDANCE'},
        {'args': {'until': '2025-01-01', 'since': '2024-02-01'}, 'report_type': 'RENEWAL_GUIDANCE'},
    ]
    for arg in command_args:
        handle_build_exception(
            {**env_vars, 'METRICS_UTILITY_REPORT_TYPE': arg['report_type']},
            arg['args'],
            'The --until parameter is not allowed when environment variable METRICS_UTILITY_REPORT_TYPE is RENEWAL_GUIDANCE',
            caplog,
        )


def test_invalid_month_format(caplog):
    bad_inputs = ['abc', '12', 'mo3', '3mon', '3months', '3m', '3mo']

    for bad_input in bad_inputs:
        handle_build_exception(env_vars, {'month': bad_input}, 'Invalid --month format. Supported date format: YYYY-MM', caplog)


def handle_build_exception(env_vars, params, error_message, caplog):
    with caplog.at_level('ERROR'):
        with pytest.raises(SystemExit) as exc_info:
            run_build_int(env_vars, params)
    log_output = '\n'.join(caplog.messages)
    assert error_message in log_output, f'Expected error message not found in logs: {exc_info.value}'


def test_invalid_argument_format(caplog):
    import metrics_utility.management.commands.gather_automation_controller_billing_data as GatherBase

    bad_inputs = [
        '2',
        '2y',
        'mo3',
        '3weeks',
        '3w',
    ]
    args = ['until', 'since']

    for bad_input in bad_inputs:
        for arg in args:
            help_text = GatherBase.help_since if arg == 'since' else GatherBase.help_until
            if bad_input == '2':
                help_text = 'Integers are not allowed for parameters --since and --until.'
            handle_build_exception(env_vars, {arg: bad_input}, help_text, caplog)
