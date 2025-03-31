from datetime import datetime

import openpyxl
import pytest

from conftest import temporary_env, transform_sheet
from pandas import Timestamp, read_excel

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
file_path = './metrics_utility/test/test_data/reports/2025/02/CCSPv2-2025-02-25--2025-02-26.xlsx'
date_today = datetime.now().strftime('%b %d, %Y')


@pytest.mark.filterwarnings('ignore::ResourceWarning')
@pytest.mark.parametrize(
    'cleanup',
    [
        file_path,
    ],
    indirect=True,
)
def test_command(cleanup):
    build_workbook('indirectly_managed_nodes')
    build_workbook('indirectly_managed_nodes,managed_nodes_by_organizations')
    # indirectly_managed_nodes_workbook = None
    try:
        ## Loads workbook for both reports
        indirectly_managed_nodes_workbook = openpyxl.load_workbook(filename=file_path)
        indirectly_managed_nodes_and_managed_by_orgs_workbook = openpyxl.load_workbook(filename=file_path)
        indirectly_managed_nodes_only_sheet = read_excel(file_path, sheet_name='Indirectly Managed nodes')
        indirectly_managed_nodes_managed_by_orgs_sheet = read_excel(file_path, sheet_name='Indirectly Managed nodes')
        for sheet in [indirectly_managed_nodes_only_sheet, indirectly_managed_nodes_managed_by_orgs_sheet]:
            validate_indirect_managed_nodes(sheet)
            validate_indirect_managed_nodes(sheet)
            validate_usage_by_organization(sheet)

        validate_columns(indirectly_managed_nodes_managed_by_orgs_sheet, indirectly_managed_nodes_managed_by_orgs_sheet)
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


def validate_managed_nodes(sheet):
    assert transform_sheet(sheet.to_dict()) == {
        0: {
            'Automated by organizations': 1,
            'First automation': Timestamp('2025-02-25 08:35:52.345000'),
            'Host name': 'host_1',
            'Job runs': 4,
            'Last automation': Timestamp('2025-02-25 08:39:08.049000'),
            'Number of task runs': 16,
        },
        1: {
            'Automated by organizations': 1,
            'First automation': Timestamp('2025-02-25 08:35:52.345000'),
            'Host name': 'host_2',
            'Job runs': 2,
            'Last automation': Timestamp('2025-02-25 08:39:08.049000'),
            'Number of task runs': 8,
        },
        2: {
            'Automated by organizations': 1,
            'First automation': Timestamp('2025-02-25 08:35:52.345000'),
            'Host name': 'localhost',
            'Job runs': 19,
            'Last automation': Timestamp('2025-02-25 12:27:58.985000'),
            'Number of task runs': 66,
        },
    }


def validate_indirect_managed_nodes(sheet):
    assert transform_sheet(sheet.to_dict()) == {
        0: {
            'Automated by organizations': 1,
            'Canonical Facts': '{"ansible_vmware_moid": ["vm-87211", "vm-87212", "vm-87213"], '
            '"ansible_vmware_bios_uuid": ["420b1367-1e11-c9d7-4d0f-c3b3cba9ae16", '
            '"420b188b-16f2-a839-756d-c627378fdcb2", '
            '"420ba1d2-3793-215c-30f0-5957a405d4e6"], '
            '"ansible_vmware_instance_uuid": '
            '["500b1a63-d55d-bf21-c104-1617888dd7d2", '
            '"500b3d2e-9abe-8ee1-98ea-bf67b591c104", '
            '"500bb935-a219-17d7-8e7e-9296f3af6be2"]}',
            'Events': '["vmware.vmware.guest_info"]',
            'Facts': '{"device_type": ["VM"]}',
            'First automation': Timestamp('2025-02-25 09:33:11.557000'),
            'Host name': 'indirect_host_1',
            'Job runs': 7,
            'Last automation': Timestamp('2025-02-25 10:48:56.984000'),
            'Manage Node Types': '["INDIRECT"]',
            'Number of task runs': 14,
        },
        1: {
            'Automated by organizations': 1,
            'Canonical Facts': '{"ansible_vmware_moid": ["vm-87212", "vm-87213"], '
            '"ansible_vmware_bios_uuid": ["420b1367-1e11-c9d7-4d0f-c3b3cba9ae16", '
            '"420ba1d2-3793-215c-30f0-5957a405d4e6"], '
            '"ansible_vmware_instance_uuid": '
            '["500b1a63-d55d-bf21-c104-1617888dd7d2", '
            '"500b3d2e-9abe-8ee1-98ea-bf67b591c104"]}',
            'Events': '["vmware.vmware.guest_info"]',
            'Facts': '{"device_type": ["VM"]}',
            'First automation': Timestamp('2025-02-25 10:48:57.035000'),
            'Host name': 'indirect_host_2',
            'Job runs': 5,
            'Last automation': Timestamp('2025-02-25 13:42:53.114000'),
            'Manage Node Types': '["INDIRECT"]',
            'Number of task runs': 10,
        },
    }


def validate_usage_by_organization(sheet):
    assert transform_sheet(sheet.to_dict()) == {
        0: {
            'Job runs': 19,
            'Non-unique indirect managed nodes automated': 12,
            'Non-unique managed nodes automated': 25,
            'Number of task runs': 114,
            'Organization name': 'Default',
            'Unique indirect managed nodes automated': 2,
            'Unique managed nodes automated': 3,
        },
    }


def validate_columns(sheet1, sheet2):
    ##Grabs column titles from both sheets
    sheet1_columns = [col.title() for col in sheet1.columns]
    sheet2_columns = [col.title() for col in sheet2.columns]

    ## Asserts that all column titles exist in both sheets
    for sheet1_columns in sheet1:
        for sheet2_columns in sheet2:
            assert sheet1_columns in sheet2 and sheet2_columns in sheet1
