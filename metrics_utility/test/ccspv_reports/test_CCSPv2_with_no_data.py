import pytest

from conftest import validate_sheet_columns, validate_sheet_tab_names

from metrics_utility.test.util import run_build_ext


env_vars = {
    'METRICS_UTILITY_PRICE_PER_NODE': '11.55',
    'METRICS_UTILITY_REPORT_RHN_LOGIN': 'test_login',
    'METRICS_UTILITY_SHIP_PATH': './metrics_utility/test/test_data',
    'METRICS_UTILITY_REPORT_SKU_DESCRIPTION': 'EX: Red Hat Ansible Automation Platform, Full Support (1 Managed Node, Dedicated, Monthly)',
    'METRICS_UTILITY_REPORT_H1_HEADING': 'CCSP NA Direct Reporting Template',
    'METRICS_UTILITY_REPORT_PO_NUMBER': '123',
    'METRICS_UTILITY_SHIP_TARGET': 'directory',
    'METRICS_UTILITY_REPORT_COMPANY_NAME': 'Partner A',
    'METRICS_UTILITY_REPORT_SKU': 'MCT3752MO',
    'METRICS_UTILITY_REPORT_EMAIL': 'email@email.com',
    'METRICS_UTILITY_REPORT_TYPE': 'CCSPv2',
}

file_path = './metrics_utility/test/test_data/reports/2024/02/CCSPv2-2024-01.xlsx'

expected_sheets = {
    'Managed nodes': [
        {'Host name': [None, None, None]},
        {'Automated by organizations': [None, None, None]},
        {'Job runs': [None, None, None]},
        {'Number of task runs': [None, None, None]},
        {'first automation': [None, None, None]},
        {'last automation': [None, None, None]},
    ],
}


@pytest.mark.filterwarnings('ignore::ResourceWarning')
@pytest.mark.parametrize(
    'cleanup',
    [
        file_path,
    ],
    indirect=True,
)
def test_command(cleanup):
    """Build xlsx report using build command and test its contents."""

    run_build_ext(env_vars, ['--month=2024-01', '--force'])

    validate_sheet_columns(file_path, expected_sheets, 14)
    validate_sheet_tab_names(file_path, expected_sheets)
