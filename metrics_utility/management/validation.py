import logging
import os
import re

from dateutil import parser

from metrics_utility.automation_controller_billing.helpers import (
    ALLOWED_EPHEMERAL_PATTERN,
    SINCE_AND_UNTIL_BUILD_PATTERN,
    SINCE_AND_UNTIL_GATHER_PATTERN,
    parse_date_param,
)
from metrics_utility.exceptions import BadParameter, MissingRequiredEnvVar, MissingRequiredParameter, UnparsableParameter


logger = logging.getLogger(__name__)

ship_path_description = 'place for collected data and built reports'


def handle_directory_ship_target():
    ship_path = os.getenv('METRICS_UTILITY_SHIP_PATH', None)

    if not ship_path:
        raise MissingRequiredEnvVar(f'Missing required env variable METRICS_UTILITY_SHIP_PATH - {ship_path_description}')

    return {'ship_path': ship_path}


def handle_s3_ship_target():
    ship_path = os.getenv('METRICS_UTILITY_SHIP_PATH', None)
    bucket_name = os.getenv('METRICS_UTILITY_BUCKET_NAME', None)
    bucket_endpoint = os.getenv('METRICS_UTILITY_BUCKET_ENDPOINT', None)
    bucket_region = os.getenv('METRICS_UTILITY_BUCKET_REGION', None)  # optional

    # S3 credentials
    bucket_access_key = os.getenv('METRICS_UTILITY_BUCKET_ACCESS_KEY', None)
    bucket_secret_key = os.getenv('METRICS_UTILITY_BUCKET_SECRET_KEY', None)

    missing = []
    if not bucket_name:
        missing += ['METRICS_UTILITY_BUCKET_NAME - name of S3 bucket']
    if not bucket_endpoint:
        missing += ['METRICS_UTILITY_BUCKET_ENDPOINT - S3 endpoint, eg. https://s3.us-east.example.com']
    if not bucket_access_key:
        missing += ['METRICS_UTILITY_BUCKET_ACCESS_KEY - S3 access key']
    if not bucket_secret_key:
        missing += ['METRICS_UTILITY_BUCKET_SECRET_KEY - S3 secret key']
    if not ship_path:
        missing += [f'METRICS_UTILITY_SHIP_PATH - {ship_path_description}']
    # bucket_region is optional

    if missing:
        raise MissingRequiredEnvVar(f'Missing some required env variables for S3 configuration, namely: {", ".join(missing)}.')

    # S3Handler params
    return {
        'ship_path': ship_path,
        'bucket_name': bucket_name,
        'bucket_endpoint': bucket_endpoint,
        'bucket_region': bucket_region,
        'bucket_access_key': bucket_access_key,
        'bucket_secret_key': bucket_secret_key,
    }


def handle_not_s3():
    surplus = []

    if os.getenv('METRICS_UTILITY_BUCKET_ACCESS_KEY', None):
        surplus += ['METRICS_UTILITY_BUCKET_ACCESS_KEY']
    if os.getenv('METRICS_UTILITY_BUCKET_ENDPOINT', None):
        surplus += ['METRICS_UTILITY_BUCKET_ENDPOINT']
    if os.getenv('METRICS_UTILITY_BUCKET_NAME', None):
        surplus += ['METRICS_UTILITY_BUCKET_NAME']
    if os.getenv('METRICS_UTILITY_BUCKET_REGION', None):
        surplus += ['METRICS_UTILITY_BUCKET_REGION']
    if os.getenv('METRICS_UTILITY_BUCKET_SECRET_KEY', None):
        surplus += ['METRICS_UTILITY_BUCKET_SECRET_KEY']

    if surplus:
        logger.warning(f'Ignoring env variables used without METRICS_UTILITY_SHIP_TARGET="s3": {", ".join(surplus)}')


def handle_crc_ship_target():
    billing_provider = os.getenv('METRICS_UTILITY_BILLING_PROVIDER', None)
    red_hat_org_id = os.getenv('METRICS_UTILITY_RED_HAT_ORG_ID', None)

    billing_provider_params = {'billing_provider': billing_provider}
    if billing_provider == 'aws':
        billing_account_id = os.getenv('METRICS_UTILITY_BILLING_ACCOUNT_ID', None)
        if not billing_account_id:
            raise MissingRequiredEnvVar('Env var: METRICS_UTILITY_BILLING_ACCOUNT_ID, containing  AWS 12 digit customer id needs to be provided.')
        billing_provider_params['billing_account_id'] = billing_account_id
    else:
        raise MissingRequiredEnvVar('Uknown METRICS_UTILITY_BILLING_PROVIDER env var, supported values are [aws].')

    if red_hat_org_id:
        billing_provider_params['red_hat_org_id'] = red_hat_org_id

    # only used for the other modes
    ship_path = os.getenv('METRICS_UTILITY_SHIP_PATH', None)
    if ship_path:
        allowed = '", "'.join(['controller_db', 'directory', 's3'])
        logger.warning(f'Ignoring METRICS_UTILITY_SHIP_PATH used without METRICS_UTILITY_SHIP_TARGET="{allowed}"')

    return billing_provider_params


def handle_not_crc():
    surplus = []

    if os.getenv('METRICS_UTILITY_BILLING_ACCOUNT_ID', None):
        surplus += ['METRICS_UTILITY_BILLING_ACCOUNT_ID']
    if os.getenv('METRICS_UTILITY_BILLING_PROVIDER', None):
        surplus += ['METRICS_UTILITY_BILLING_PROVIDER']
    if os.getenv('METRICS_UTILITY_RED_HAT_ORG_ID', None):
        surplus += ['METRICS_UTILITY_RED_HAT_ORG_ID']

    if surplus:
        logger.warning(f'Ignoring env variables used without METRICS_UTILITY_SHIP_TARGET="crc": {", ".join(surplus)}')


def handle_validate_date_param(param, help_text, command):
    exceptions = []

    if param is None:
        return

    if param.isdigit():
        """If the value is a digit stop execution and render the failure message."""
        exceptions.append('isdigit')
        help_text = 'Integers are not allowed for parameters --since and --until.'
        raise UnparsableParameter(help_text)

    try:
        """Try to parse the date, and if it fails go to next loop iteration.  Then, determine if we need to render the failure message."""
        parser.parse(param)
    except Exception:
        exceptions.append(help_text)

        """Try to parse the date, and if it fails go to next loop iteration.  Then, determine if we need to render the failure message."""
    if command == 'build':
        match = match_build_date_param_regex(param)
    elif command == 'gather':
        match = match_gather_date_param_regex(param)
    if match is None:
        exceptions.append(help_text)
    if len(exceptions) > 1:
        raise UnparsableParameter(help_text)


def match_build_date_param_regex(date):
    return re.match(SINCE_AND_UNTIL_BUILD_PATTERN, date)


def match_gather_date_param_regex(date):
    return re.match(SINCE_AND_UNTIL_GATHER_PATTERN, date)


def validate_build_extra_params(help_text, options):
    opt_month = options.get('month') or None
    # since = None
    until = options.get('until', None)
    since = options.get('since', None)
    since_help = help_text.get('since')
    until_help = help_text.get('until')
    # until = None
    handle_validate_ephemeral_param(options.get('ephemeral', None), help_text.get('ephemeral'))
    handle_validate_date_param(since, since_help, 'build')
    handle_validate_date_param(until, until_help, 'build')

    report_type = os.getenv('METRICS_UTILITY_REPORT_TYPE', None)
    if report_type is None:
        return

    until = parse_date_param(until)
    since = parse_date_param(since)

    has_since = since is not None
    has_until = until is not None

    validate_renewal_guidance_params(has_since, has_until, help_text)

    if (has_since and has_until) and until < since:
        raise UnparsableParameter('The date for --until cannot be before the date for --since.')

    if (has_since or has_until) and opt_month is not None:
        raise BadParameter('The --since and --until parameters are not allowed if the --month parameter is provided.')


def validate_renewal_guidance_params(since, until, help_text):
    report_type = os.getenv('METRICS_UTILITY_REPORT_TYPE', None)
    is_renewal = report_type.startswith('RENEWAL_GUIDANCE')
    if not is_renewal:
        return

    since_help = help_text.get('since')
    until_help = help_text.get('until')
    if until:
        raise BadParameter('The --until parameter is not allowed when environment variable METRICS_UTILITY_REPORT_TYPE is RENEWAL_GUIDANCE')

    if since:
        raise MissingRequiredParameter(f"""{help_text.time_frame_extra_params} \n\n{since_help} \n{until_help} \n{help_text.month}""")


def handle_validate_ephemeral_param(value, help):
    report_type = os.getenv('METRICS_UTILITY_REPORT_TYPE', None)
    if not value:
        return
    if not report_type.startswith('RENEWAL_GUIDANCE'):
        raise BadParameter(f'METRICS_UTILITY_REPORT_TYPE {report_type} does not allow --ephemeral.')
    if re.match(ALLOWED_EPHEMERAL_PATTERN, value):
        return
    raise UnparsableParameter(help)
