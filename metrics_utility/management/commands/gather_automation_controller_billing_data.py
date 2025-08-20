import os

from argparse import RawDescriptionHelpFormatter

from django.core.management.base import BaseCommand

from metrics_utility.automation_controller_billing.collector import Collector
from metrics_utility.exceptions import (
    BadShipTarget,
    NoAnalyticsCollected,
)
from metrics_utility.logger import debug, logger
from metrics_utility.management.help_text import HelpTextGenerator
from metrics_utility.management.validation import (
    handle_crc_ship_target,
    handle_directory_ship_target,
    handle_env_validation,
    handle_not_crc,
    handle_not_s3,
    handle_s3_ship_target,
    parse_date_param,
)


class Command(BaseCommand):
    """
    Gather Automation Controller billing data
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.help_generator = HelpTextGenerator()
        self.help = self.help_generator.gather_help_title
        self.help_texts = self.help_generator.gather_param_help_texts

    def create_parser(self, prog_name, subcommand, **kwargs):
        # Delay property evaluation until help is actually displayed
        parser = super().create_parser(
            prog_name,
            subcommand,
            formatter_class=RawDescriptionHelpFormatter,
            **kwargs,
        )
        # Set epilog dynamically
        parser.epilog = self.help_generator.gather_env_var_help_text
        return parser

    def add_arguments(self, parser):
        help_texts = self.help_generator.gather_param_help_texts
        parser.add_argument('--dry-run', dest='dry-run', action='store_true', help=help_texts.get('dry-run'))
        parser.add_argument('--ship', dest='ship', action='store_true', help=help_texts.get('ship'))
        parser.add_argument('--since', dest='since', action='store', help=help_texts.get('since'))
        parser.add_argument('--until', dest='until', action='store', help=help_texts.get('until'))
        parser.add_argument('--verbose', dest='verbose', action='store_true', help=help_texts.get('verbose'))

    def handle(self, *args, **options):
        if options.get('verbose'):
            debug()
        handle_env_validation('gather')

        opt_since = options.get('since')
        opt_until = options.get('until')
        opt_ship = options.get('ship')
        opt_dry_run = options.get('dry-run')

        since = parse_date_param(opt_since, self.help_generator.gather_param_help_texts, 'since')
        until = parse_date_param(opt_until, self.help_generator.gather_param_help_texts, 'until')

        ship_target = os.getenv('METRICS_UTILITY_SHIP_TARGET')
        extra_params = self._handle_ship_target(ship_target)

        if opt_ship and opt_dry_run:
            logger.error('Arguments --ship and --dry-run cannot be processed at the same time, set only one of these.')
            return

        collector = Collector(
            collection_type=Collector.MANUAL_COLLECTION if opt_ship else Collector.DRY_RUN,
            ship_target=ship_target,
            billing_provider_params=extra_params,
        )

        tgzfiles = collector.gather(since=since, until=until, billing_provider_params=extra_params)
        if not tgzfiles:
            logger.error('No analytics collected')
            raise NoAnalyticsCollected('No analytics collected')
        if tgzfiles:
            logger.info('Analytics collected')

    def _handle_ship_target(self, ship_target):
        if ship_target == 'crc':
            handle_not_s3()
            return handle_crc_ship_target()
        elif ship_target == 'directory':
            handle_not_crc()
            handle_not_s3()
            return handle_directory_ship_target(self.help_generator.env_var_help_texts)
        elif ship_target == 's3':
            handle_not_crc()
            return handle_s3_ship_target(self.help_generator.env_var_help_texts)
        else:
            allowed = ', '.join(['crc', 'directory', 's3'])
            raise BadShipTarget(f'Unexpected value for METRICS_UTILITY_SHIP_TARGET env var ({ship_target}), allowed values: {allowed}')
