import os
import sys

from importlib import import_module

import django.core.management as management

from metrics_utility.exceptions import MetricsException
from metrics_utility.logger import logger


class ManagementUtility(management.ManagementUtility):
    def main_help_text(self, commands_only=False):
        """
        Return the script's main help text, as a string.
        """
        if commands_only:
            usage = sorted(self.get_commands())
        else:
            usage = [
                '',
                "Type 'manage.py help <subcommand>' for help on a specific subcommand.",
                '',
                'Available subcommands:',
            ]
            commands_dict = self.get_commands()

            # First show custom commands with detailed help
            custom_commands = ['build_report', 'gather_automation_controller_billing_data']
            for name in sorted(custom_commands):
                if name in commands_dict:
                    usage.append('')
                    app_name = commands_dict[name]
                    try:
                        command = self.fetch_command(name)
                        help_text = command.help if hasattr(command, 'help') else 'No help available'
                        usage.append(f'[{app_name}]')
                        usage.append(f'    {name}')
                        usage.append(f'        {help_text}')
                        if hasattr(command, 'help_generator'):
                            # Add environment variable help sections
                            if name == 'build_report':
                                usage.append('')
                                usage.append('        Environment Variables for build_report:')
                                # Use the existing help text generator logic
                                ship_target = os.getenv('METRICS_UTILITY_SHIP_TARGET')
                                all_sections = {
                                    **command.help_generator.build_report_env_var_help_texts,
                                    **command.help_generator.env_vars_for_build_and_gather,
                                }
                                for section_key, section_data in all_sections.items():
                                    section_lines = command.help_generator.format_help_text_section(section_key, section_data, ship_target)
                                    # Adjust indentation for main help context (add 6 spaces to each line)
                                    for line in section_lines:
                                        if line.strip():  # Only indent non-empty lines
                                            usage.append(f'      {line}')
                                        else:
                                            usage.append('')
                            elif name == 'gather_automation_controller_billing_data':
                                usage.append('')
                                usage.append('        Environment Variables for gather_automation_controller_billing_data:')
                                # Use the existing help text generator logic
                                all_sections = {
                                    **command.help_generator.gather_env_var_help_texts,
                                    **command.help_generator.env_vars_for_build_and_gather,
                                }
                                for section_key, section_data in all_sections.items():
                                    section_lines = command.help_generator.format_help_text_section(section_key, section_data, ship_target)
                                    # Adjust indentation for main help context (add 6 spaces to each line)
                                    for line in section_lines:
                                        if line.strip():  # Only indent non-empty lines
                                            usage.append(f'      {line}')
                                        else:
                                            usage.append('')
                    except Exception:
                        usage.append(f'[{app_name}]')
                        usage.append(f'    {name}')

            # Then show Django built-in commands in a separate section
            django_commands = [name for name in sorted(commands_dict) if name not in custom_commands]
            if django_commands:
                usage.append('')
                usage.append('')
                usage.append('[django]')
                for name in django_commands:
                    usage.append(f'    {name}')
        return '\n'.join(usage)

    def execute(self):
        """
        Given the command-line arguments, figure out which subcommand is being
        run, create a parser appropriate to that command, and run it.
        """
        try:
            subcommand = self.argv[1]
        except IndexError:
            subcommand = 'help'  # Display help if no arguments were given.

        # Preprocess options to extract --settings and --pythonpath.
        # These options could affect the commands that are available, so they
        # must be processed early.
        parser = management.CommandParser(
            prog=self.prog_name,
            usage='%(prog)s subcommand [options] [args]',
            add_help=False,
            allow_abbrev=False,
        )
        parser.add_argument('--settings')
        # parser.add_argument("--pythonpath")
        parser.add_argument('args', nargs='*')  # catch-all
        try:
            options, args = parser.parse_known_args(self.argv[2:])
            # handle_default_options(options)
        except management.CommandError:
            pass  # Ignore any option errors at this point.

        # self.autocomplete()

        if subcommand == 'help':
            if '--commands' in args:
                sys.stdout.write(self.main_help_text(commands_only=True) + '\n')
            elif not options.args:
                sys.stdout.write(self.main_help_text() + '\n')
            else:
                self.fetch_command(options.args[0]).print_help(self.prog_name, options.args[0])
        # Special-cases: We want 'django-admin --version' and
        # 'django-admin --help' to work, for backwards compatibility.
        elif subcommand == 'version' or self.argv[1:] == ['--version']:
            # sys.stdout.write(django.get_version() + "\n")
            sys.stdout.write('0.5.1dev' + '\n')
        elif self.argv[1:] in (['--help'], ['-h']):
            sys.stdout.write(self.main_help_text() + '\n')
        else:
            self.run_subcommand(subcommand, self.argv)

    def fetch_command(self, subcommand):
        try:
            module = import_module(f'metrics_utility.management.commands.{subcommand}')
        except Exception as ex:
            sys.stdout.write(f"Failed to import command '{subcommand}': {ex}")
            raise ex

        return module.Command()

    @staticmethod
    def get_commands():
        commands = {}
        path = os.path.join(os.path.dirname(__file__), 'management')
        commands.update({name: 'metrics_utility' for name in management.find_commands(path)})
        return commands

    def run_subcommand(self, subcommand, argv):
        try:
            self.fetch_command(subcommand).run_from_argv(argv)
        except MetricsException as e:
            logger.error(e.name)
            exit(1)
        except Exception as e:
            logger.exception(e)
            exit(1)
