from datetime import datetime

import openpyxl
import pandas
import pytest

from conftest import temporary_env

from metrics_utility.management.commands.build_report import Command


env_vars = {
    'METRICS_UTILITY_PRICE_PER_NODE': '11.55',
    'METRICS_UTILITY_REPORT_RHN_LOGIN': 'test_login',
    'METRICS_UTILITY_SHIP_PATH': './metrics_utility/test/test_data',
    'METRICS_UTILITY_REPORT_END_USER_COMPANY_NAME': 'Customer A',
    'METRICS_UTILITY_REPORT_END_USER_STATE': 'TX',
    'METRICS_UTILITY_REPORT_SKU_DESCRIPTION': 'EX: Red Hat Ansible Automation Platform, Full Support (1 Managed Node, Dedicated, Monthly)',
    'METRICS_UTILITY_REPORT_H1_HEADING': 'CCSP NA Direct Reporting Template',
    'METRICS_UTILITY_REPORT_END_USER_CITY': 'Springfield',
    'METRICS_UTILITY_REPORT_PO_NUMBER': '123',
    'METRICS_UTILITY_SHIP_TARGET': 'directory',
    'METRICS_UTILITY_REPORT_END_USER_COUNTRY': 'US',
    'METRICS_UTILITY_REPORT_COMPANY_NAME': 'Partner A',
    'METRICS_UTILITY_REPORT_SKU': 'MCT3752MO',
    'METRICS_UTILITY_REPORT_EMAIL': 'email@email.com',
    'METRICS_UTILITY_REPORT_TYPE': 'CCSPv2',
}

indirect_nodes_and_managed_by_org_file_path = './metrics_utility/test/test_data/reports/2025/02/CCSPv2-2025-02-13--2025-02-13.xlsx'
indirectly_managed_nodes_file_path = './metrics_utility/test/test_data/reports/2025/02/CCSPv2-2025-02-13--2025-02-13.xlsx'
date_today = datetime.now().strftime('%b %d, %Y')


@pytest.mark.filterwarnings('ignore::ResourceWarning')
@pytest.mark.parametrize(
    'cleanup',
    [
        indirect_nodes_and_managed_by_org_file_path,
    ],
    indirect=True,
)
def test_command(cleanup):
    build_workbook('indirectly_managed_nodes')
    build_workbook('indirectly_managed_nodes,managed_nodes_by_organizations')
    # indirectly_managed_nodes_workbook = None
    try:
        ## Loads workbook for both reports
        indirectly_managed_nodes_workbook = openpyxl.load_workbook(filename=indirectly_managed_nodes_file_path)
        indirectly_managed_nodes_and_managed_by_orgs_workbook = openpyxl.load_workbook(filename=indirect_nodes_and_managed_by_org_file_path)

        ## Reads the sheets from both workbooks
        indirectly_managed_nodes_only_sheet = pandas.read_excel(indirectly_managed_nodes_file_path, sheet_name='Indirectly Managed nodes')
        indirectly_managed_nodes_managed_by_orgs_sheet = pandas.read_excel(
            indirect_nodes_and_managed_by_org_file_path, sheet_name='Indirectly Managed nodes'
        )

        ##Grabs column titles from both sheets
        indirect_managed_columns = [col.title() for col in indirectly_managed_nodes_only_sheet.columns]
        org_managed_columns = [col.title() for col in indirectly_managed_nodes_managed_by_orgs_sheet.columns]

        ## Asserts that all column titles exist in both sheets
        for indirect_managed_col in indirect_managed_columns:
            for org_managed_col in org_managed_columns:
                assert indirect_managed_col in org_managed_columns and org_managed_col in indirect_managed_columns

    finally:
        indirectly_managed_nodes_workbook.close()
        indirectly_managed_nodes_and_managed_by_orgs_workbook.close()


def build_workbook(optional_sheets):
    """Build xlsx report using build command and test its contents."""

    with temporary_env({**env_vars, 'METRICS_UTILITY_OPTIONAL_CCSP_REPORT_SHEETS': optional_sheets}):
        options = {
            'since': '2025-02-13',
            'until': '2025-02-13',
            'ephemeral': None,
            'force': True,
            'verbose': False,
        }
        command = Command()
        command.handle(**options)
