import os

from typing import Dict, List, Optional, TypedDict

from metrics_utility.management.validation import date_format_text


# Type definitions for better type safety
class EnvVarInfo(TypedDict):
    required: bool
    text: str


class EnvVarSection(TypedDict):
    title: str
    vars: Dict[str, EnvVarInfo]


# Type aliases for better readability
EnvVarConfig = Dict[str, EnvVarSection]
ParamHelpTexts = Dict[str, str]

env_vars_for_build_and_gather: EnvVarConfig = {
    'billing_provider': {
        'title': 'Billing Provider Configuration',
        'vars': {
            'METRICS_UTILITY_BILLING_PROVIDER': {'required': False, 'text': "one of 'aws'"},
            'METRICS_UTILITY_BILLING_ACCOUNT_ID': {'required': False, 'text': 'AWS 12 digit customer id'},
            'METRICS_UTILITY_RED_HAT_ORG_ID': {'required': True, 'text': 'Red Hat org id'},
        },
    },
    'crc': {
        'title': 'CRC Configuration',
        'vars': {
            'METRICS_UTILITY_CRC_INGRESS_URL': {'required': False, 'text': 'CRC ingress url'},
            'METRICS_UTILITY_CRC_SSO_URL': {'required': False, 'text': 'CRC sso url'},
            'METRICS_UTILITY_PROXY_URL': {'required': False, 'text': 'Proxy url'},
            'METRICS_UTILITY_SERVICE_ACCOUNT_ID': {'required': False, 'text': 'Service account id'},
            'METRICS_UTILITY_SERVICE_ACCOUNT_SECRET': {'required': False, 'text': 'Service account secret'},
        },
    },
    's3': {
        'title': 'S3 Configuration',
        'vars': {
            'METRICS_UTILITY_BUCKET_NAME': {'required': False, 'text': 's3 bucket name to which save the report'},
            'METRICS_UTILITY_BUCKET_ENDPOINT': {'required': False, 'text': 's3 bucket endpoint'},
            'METRICS_UTILITY_BUCKET_ACCESS_KEY': {'required': False, 'text': 's3 bucket access key'},
            'METRICS_UTILITY_BUCKET_SECRET_KEY': {'required': False, 'text': 's3 bucket secret key'},
            'METRICS_UTILITY_BUCKET_REGION': {'required': False, 'text': 's3 bucket region'},
        },
    },
    'ship': {
        'title': 'Ship Configuration (Always Required)',
        'vars': {
            'METRICS_UTILITY_SHIP_TARGET': {
                'required': True,
                'text': ("one of 'directory', 's3', 'controller_db' - input/output mechanism"),
            },
            'METRICS_UTILITY_SHIP_PATH': {
                'required': True,
                'text': 'A path - local or s3 directory path, input tarballs in path/data/, output xlsx in path/reports/',
            },
        },
    },
    'installation': {
        'title': 'Installation Type Detection',
        'vars': {
            'KUBERNETES_SERVICE_PORT': {
                'required': False,
                'text': "Used by collectors' get_install_type - for k8s",
            },
            'container': {
                'required': False,
                'text': "Used by collectors' get_install_type - for oci",
            },
        },
    },
}
build_report_help_title: str = 'Build Report'
build_report_param_help_texts: ParamHelpTexts = {
    'since': (f'Start date for collection, including. {date_format_text.format(name="since")}'),
    'until': (f'End date for collection, including. {date_format_text.format(name="until")}'),
    'month': (
        'Month the report will be generated for, with format YYYY-MM. '
        "If this parameter is not provided, the previous month's report will be generated if it does not already exist."
    ),
    'ephemeral': (
        'Duration in months or days to determine if host is ephemeral. '
        'Months are considered as 30 days in duration. '
        'Example: --ephemeral=3months, or --ephemeral=3days'
    ),
    'force': ('With this option, the existing reports will be overwritten if running this command again.'),
    'verbose': ('Print debug information to console.'),
}

build_report_env_var_help_texts: EnvVarConfig = {
    'deduplication': {
        'title': 'Deduplication Configuration',
        'vars': {
            'METRICS_UTILITY_DEDUPLICATOR': {'required': False, 'text': "one of 'ccsp', 'renewal', 'ccsp-experimental'"},
            'REPORT_RENEWAL_GUIDANCE_DEDUP_ITERATIONS': {
                'required': False,
                'text': 'number of max dedup iterations, specifically for `dedup-renewal`, with the `RENEWAL_GUIDANCE` report',
            },
        },
    },
    'core': {
        'title': 'Core Configuration (Always Required)',
        'vars': {
            'METRICS_UTILITY_OPTIONAL_CCSP_REPORT_SHEETS': {'required': False, 'text': 'enables optional report sheets, comma-separated list'},
            'METRICS_UTILITY_ORGANIZATION_FILTER': {
                'required': False,
                'text': 'CCSPv2 only, `report_organization_filter` - semicolon-separated list of org names to filter by',
            },
            'METRICS_UTILITY_REPORT_TYPE': {
                'required': True,
                'text': ("one of 'CCSPv2', 'CCSP', 'RENEWAL_GUIDANCE'. Determines which kind of report is generated"),
            },
        },
    },
    # CCSP Configuration data
    'ccsp': {
        'title': 'CCSP Configuration',
        'vars': {
            'METRICS_UTILITY_PRICE_PER_NODE': {
                'required': False,
                'text': 'price_per_node / unit_price - field value and multiplied by',
            },
            'METRICS_UTILITY_REPORT_COMPANY_BUSINESS_LEADER': {
                'required': False,
                'text': 'Name of person responsible for metrics',
            },
            'METRICS_UTILITY_REPORT_COMPANY_PROCUREMENT_LEADER': {
                'required': False,
                'text': "Company's procurement person for report header",
            },
            'METRICS_UTILITY_REPORT_COMPANY_NAME': {
                'required': False,
                'text': 'Name of company',
            },
            'METRICS_UTILITY_REPORT_EMAIL': {
                'required': False,
                'text': 'Email used for reports',
            },
            'METRICS_UTILITY_REPORT_END_USER_CITY': {
                'required': False,
                'text': 'City of end user company',
            },
            'METRICS_UTILITY_REPORT_END_USER_COMPANY_NAME': {
                'required': False,
                'text': 'Name of end user company',
            },
            'METRICS_UTILITY_REPORT_END_USER_COUNTRY': {
                'required': False,
                'text': 'Country of end user company',
            },
            'METRICS_UTILITY_REPORT_END_USER_STATE': {
                'required': False,
                'text': 'State of end user company',
            },
            'METRICS_UTILITY_REPORT_H1_HEADING': {
                'required': False,
                'text': 'Heading for report',
            },
            'METRICS_UTILITY_REPORT_PO_NUMBER': {
                'required': False,
                'text': 'Purchase order number',
            },
            'METRICS_UTILITY_REPORT_RHN_LOGIN': {
                'required': False,
                'text': 'Red Hat Network login',
            },
            'METRICS_UTILITY_REPORT_SKU': {
                'required': False,
                'text': 'SKU',
            },
            'METRICS_UTILITY_REPORT_SKU_DESCRIPTION': {
                'required': False,
                'text': 'SKU description',
            },
        },
    },
}

gather_env_var_help_texts: EnvVarConfig = {
    'gather': {
        'title': 'Gather automation controller billing data',
        'vars': {
            'METRICS_UTILITY_CLUSTER_NAME': {
                'required': False,
                'text': '`total_workers_vcpu` collector payload `.cluster_name` (required when that collector is enabled)',
            },
            'METRICS_UTILITY_COLLECTOR_LOCK_SUFFIX': {'required': False, 'text': 'total_workers_vcpu collector custom lock name'},
            'METRICS_UTILITY_DISABLE_JOB_HOST_SUMMARY_COLLECTOR': {
                'required': False,
                'text': 'disable `job_host_summary` collector (use together with `METRICS_UTILITY_OPTIONAL_COLLECTORS`)',
            },
            'METRICS_UTILITY_DISABLE_SAVE_LAST_GATHERED_ENTRIES': {
                'required': False,
                'text': 'Skip updating last gather info from controller settings',
            },
            'METRICS_UTILITY_MAX_GATHER_PERIOD_DAYS': {
                'required': False,
                'text': 'Maximum length of collection interval in days, default 28; `get_max_gather_period_days`',
            },
            'METRICS_UTILITY_OPTIONAL_COLLECTORS': {'required': False, 'text': 'Optional collectors, comma-separated list'},
            'METRICS_UTILITY_USAGE_BASED_BILLING_ENABLED': {
                'required': False,
                'text': '`total_workers_vcpu` collector toggle - skips kubernetes when disabled (default: false)',
            },
        },
    },
}
gather_help_title: str = 'Gather Automation Controller billing data'
gather_param_help_texts: ParamHelpTexts = {
    'since': (f'Start date for collection, including. {date_format_text.format(name="since")}'),
    'until': (f'End date for collection, including. {date_format_text.format(name="until")}'),
    'dry-run': ('Gather billing metrics without shipping.'),
    'ship': ('Enable shipping of billing metrics to the console.redhat.com'),
    'verbose': ('Print debug information to console.'),
}


class HelpTextGenerator:
    """Class to generate environment variable help text."""

    def __init__(self) -> None:
        self.build_report_env_var_help_texts: EnvVarConfig = build_report_env_var_help_texts
        self.gather_env_var_help_texts: EnvVarConfig = gather_env_var_help_texts
        self.gather_help_title: str = gather_help_title
        self.gather_param_help_texts: ParamHelpTexts = gather_param_help_texts
        self.build_report_param_help_texts: ParamHelpTexts = build_report_param_help_texts
        self.build_report_help_title: str = build_report_help_title
        self.env_vars_for_build_and_gather: EnvVarConfig = env_vars_for_build_and_gather

    @property
    def build_report_env_var_help_text(self) -> str:
        lines: List[str] = []
        ship_target: Optional[str] = os.getenv('METRICS_UTILITY_SHIP_TARGET')

        # Combine both dictionaries for build_report command
        all_sections: EnvVarConfig = {**self.build_report_env_var_help_texts, **self.env_vars_for_build_and_gather}

        for section_key, section_data in all_sections.items():
            lines.extend(self.format_help_text_section(section_key, section_data, ship_target))

        return self._ensure_trailing_newlines('\n'.join(lines))

    @property
    def gather_env_var_help_text(self) -> str:
        lines: List[str] = []
        ship_target: Optional[str] = os.getenv('METRICS_UTILITY_SHIP_TARGET')

        # Combine both dictionaries for gather command
        all_sections: EnvVarConfig = {**self.gather_env_var_help_texts, **self.env_vars_for_build_and_gather}

        for section_key, section_data in all_sections.items():
            lines.extend(self.format_help_text_section(section_key, section_data, ship_target))

        return self._ensure_trailing_newlines('\n'.join(lines))

    def format_help_text_section(self, section_key: str, section_data: EnvVarSection, ship_target: Optional[str]) -> List[str]:
        lines: List[str] = []

        # Add section title
        lines.append('')  # Empty line before section
        lines.append(f'   {section_data["title"]}:')
        lines.append('')  # Empty line after title

        # Add variables in this section
        for var_name, var_info in section_data['vars'].items():
            # Determine if required based on current context
            required_text: str
            if section_key == 's3' and ship_target == 's3':
                required_text = 'required'
            elif var_info['required'] is True:
                required_text = 'required'
            elif var_info['required'] is False:
                required_text = 'optional'
            else:
                required_text = str(var_info['required'])

            lines.append(f'  {var_name} ({required_text}): {var_info["text"]}')

        return lines

    def _ensure_trailing_newlines(self, text: str, count: int = 4) -> str:
        """Ensure text ends with specified number of newlines."""
        # Add newlines with a non-breaking space to prevent stripping
        return text.rstrip() + '\n' * count + ' '

    @property
    def env_var_help_texts(self) -> Dict[str, EnvVarInfo]:
        """Backward compatibility: flatten all env vars into single dict for validation functions."""
        flattened: Dict[str, EnvVarInfo] = {}

        # Flatten build_report env vars
        for section_data in self.build_report_env_var_help_texts.values():
            for var_name, var_info in section_data['vars'].items():
                flattened[var_name] = var_info

        # Flatten shared env vars
        for section_data in self.env_vars_for_build_and_gather.values():
            for var_name, var_info in section_data['vars'].items():
                flattened[var_name] = var_info

        return flattened


# Create a singleton instance for easy import
help_generator = HelpTextGenerator()
