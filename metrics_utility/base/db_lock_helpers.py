from contextlib import contextmanager
from zlib import crc32

from django.db import DEFAULT_DB_ALIAS, connection, connections

from metrics_utility.logger import logger


@contextmanager
def _pglocks_advisory_lock(key, shared=False, wait=False, db_alias=DEFAULT_DB_ALIAS):
    function_name, release_function_name = _generate_function_name(wait, shared)
    generated_key = _validate_and_create_generated_key(key)
    tuple_format = False
    if not isinstance(generated_key, int):
        raise ValueError('Cannot use %s as a lock id' % generated_key)
    if tuple_format:
        base = 'SELECT %s(%d, %d)'
        params = (generated_key[0], generated_key[1])
    else:
        base = 'SELECT %s(%d)'
        params = (generated_key,)
    acquire_params = (function_name,) + params
    command = base % acquire_params

    with connections[db_alias].cursor() as cursor:
        cursor.execute(command)

        if not wait:
            acquired = cursor.fetchone()[0]
        else:
            acquired = True
        try:
            yield acquired
        finally:
            if acquired:
                release_params = (release_function_name,) + params

                command = base % release_params
                cursor.execute(command)


@contextmanager
def advisory_lock(*args, lock_session_timeout_milliseconds=0, **kwargs):
    idle_in_transaction_session_timeout = None
    idle_session_timeout = None
    try:
        # Set session timeouts if requested
        if lock_session_timeout_milliseconds > 0:
            with connection.cursor() as cur:
                idle_in_transaction_session_timeout = cur.execute('SHOW idle_in_transaction_session_timeout').fetchone()[0]
                idle_session_timeout = cur.execute('SHOW idle_session_timeout').fetchone()[0]
                cur.execute('SET idle_in_transaction_session_timeout = %s', (lock_session_timeout_milliseconds,))
                cur.execute('SET idle_session_timeout = %s', (lock_session_timeout_milliseconds,))

        # Acquire the lock and yield to caller
        with _pglocks_advisory_lock(*args, **kwargs) as internal_lock:
            yield internal_lock
    finally:
        _restore_timeout_values(lock_session_timeout_milliseconds, idle_in_transaction_session_timeout, idle_session_timeout)


def _generate_function_name(wait, shared):
    function_name = 'pg_'
    release_function_name = 'pg_advisory_unlock'
    if not wait:
        function_name += 'try_'
    function_name += 'advisory_lock'
    if shared:
        function_name += '_shared'
        release_function_name += '_shared'

    return function_name, release_function_name


def _validate_tuple(key):
    if len(key) != 2:
        raise ValueError('Tuples and lists as lock IDs must have exactly two entries.')
    if not isinstance(key[0], int) or not isinstance(key[1], int):
        raise ValueError('Both members of a tuple/list lock ID must be integers')
    return True


def _validate_and_create_generated_key(key):
    if isinstance(key, (list, tuple)):
        # Validate the tuple/list format
        _validate_tuple(key)
        # Convert tuple to deterministic string, then use CRC32 like strings
        # This ensures consistent results across Python restarts
        tuple_str = f'{key[0]}:{key[1]}'
        pos = crc32(tuple_str.encode('utf-8'))
        # Convert to non-negative range [0, 2^31-1]
        generated_key = pos % (2**31)
    elif isinstance(key, str):
        # Convert string to integer using CRC32
        pos = crc32(key.encode('utf-8'))
        # Convert to non-negative range [0, 2^31-1]
        generated_key = pos % (2**31)
    elif isinstance(key, int):
        # Use integer as-is, but ensure it's in valid range
        # Convert to non-negative range [0, 2^31-1]
        generated_key = abs(key) % (2**31)
    else:
        raise ValueError('Cannot use %s as a lock id' % key)
    return generated_key


def _restore_timeout_values(lock_session_timeout_milliseconds, idle_in_transaction_session_timeout, idle_session_timeout):
    try:
        if lock_session_timeout_milliseconds > 0:
            with connection.cursor() as cur:
                if idle_in_transaction_session_timeout is not None:
                    cur.execute('SET idle_in_transaction_session_timeout = %s', (idle_in_transaction_session_timeout,))
                if idle_session_timeout is not None:
                    cur.execute('SET idle_session_timeout = %s', (idle_session_timeout,))
    except Exception as e:
        logger.error(f'Error restoring timeout values: {e}')
