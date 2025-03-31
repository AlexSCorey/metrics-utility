import logging

import pandas as pd

from metrics_utility.automation_controller_billing.dataframe_engine.base import Base
from metrics_utility.automation_controller_billing.helpers import merge_arrays, merge_json_sets, parse_json_array
from metrics_utility.debug_utils import print_data, print_debug
from metrics_utility.metric_utils import DIRECT, INDIRECT, MANAGED_NODE_TYPES


logger = logging.getLogger(__name__)

#######################################
# Code for building of the dataframe report based on JobhostSummary table
######################################


class DataframeCollectionStatus(Base):
    LOG_PREFIX = '[AAPBillingReport] '

    def build_dataframe(self):
        # A daily rollup dataframe
        billing_data_monthly_rollup = None

        for date in self.dates():
            ###############################
            # Generate the monthly dataset for report
            ###############################
            breakpoint()
            for data in self.extractor.iter_batches(date=date):
                # If the dataframe is empty, skip additional processing
                billing_data = data['data_collection_status']
                print_data(billing_data, 'Newly loaded data')



                billing_data['elapsed_time'] = billing_data['collection_start_timestamp'] - billing_data['until']

                main_jobhost = data['main_jobhost']
                summary_hosts = data['job_host_summary']
                if main_jobhost is not None:
                    billing_data['hosts'] = main_jobhost['host_name']

                if summary_hosts is not None:
                    billing_data['hosts']=summary_hosts['host_name']
                billing_data['hosts']=billing_data['hosts'].nunique()

                if 'job_created' in billing_data:
                    billing_data['job_created'] = pd.to_datetime(billing_data['job_created']).dt.tz_localize(None)
                else:
                    billing_data['job_created'] = pd.NaT

                ################################
                # Do the aggregation
                ################################
                print_data(billing_data, 'New loaded data batch')
                billing_data_group = billing_data.groupby(self.unique_index_columns(), dropna=False).agg(
                    elapsed_time=('task_runs', 'sum'),

                    # host_runs=('host_name', 'count'),
                    # first_automation=('created', 'min'),
                    # last_automation=('created', 'max'),
                    # job_created=('job_created', 'max'),
                    # managed_node_type=('managed_node_type', 'min'),
                    # manage_node_types=('managed_node_type_string', lambda x: set(x)),
                    # # TODO: optimize the aggregation to keep less rows around
                    # # job_ids=('inventory_name', lambda x: set(x)),
                    # events=('events', lambda x: merge_arrays(x)),
                    # canonical_facts=('canonical_facts', lambda x: merge_json_sets(x)),
                    # facts=('facts', lambda x: merge_json_sets(x)),
                )

                print_data(billing_data_group, 'New data batch after aggregation')

                # Tweak types to match the table
                billing_data_group = self.cast_dataframe(billing_data_group, self.cast_types())

                ################################
                # Merge aggregations of multiple batches
                ################################
                if billing_data_monthly_rollup is None:
                    billing_data_monthly_rollup = billing_data_group
                else:
                    # Multipart collection, merge the dataframes and sum counts
                    billing_data_monthly_rollup = pd.merge(
                        billing_data_monthly_rollup.loc[:,], billing_data_group.loc[:,], on=self.unique_index_columns(), how='outer'
                    )
                    print_data(billing_data_monthly_rollup, 'Global data outer join batch data')

                    billing_data_monthly_rollup = self.summarize_merged_dataframes(
                        billing_data_monthly_rollup,
                        self.data_columns(),
                        operations={
                            'first_automation': 'min',
                            'last_automation': 'max',
                            'job_created': 'max',
                            'managed_node_type': 'min',
                            'manage_node_types': 'combine_set',
                            'events': 'combine_set',
                            'canonical_facts': 'combine_json_values',
                            'facts': 'combine_json_values',
                        },
                    )

                    # Tweak types to match the table
                    billing_data_monthly_rollup = self.cast_dataframe(billing_data_monthly_rollup, self.cast_types())

                print_data(billing_data_monthly_rollup, 'Actual global data')

        if billing_data_monthly_rollup is None:
            return None

        return billing_data_monthly_rollup.reset_index()

    @staticmethod
    def unique_index_columns():
        return ['organization_name', 'job_template_name', 'host_name', 'original_host_name', 'install_uuid', 'job_remote_id']

    @staticmethod
    def data_columns():
        return [
            'host_runs',
            'task_runs',
            'first_automation',
            'last_automation',
            'job_created',
            'managed_node_type',
            'manage_node_types',
            'canonical_facts',
            'facts',
            'events',
        ]

    @staticmethod
    def cast_types():
        return {
            'task_runs': int,
            'host_runs': int,
            'managed_node_type': int,
            'first_automation': 'datetime64[ns]',
            'last_automation': 'datetime64[ns]',
            'job_created': 'datetime64[ns]',
        }
