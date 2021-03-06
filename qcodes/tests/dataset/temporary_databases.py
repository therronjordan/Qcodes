import tempfile
import gc
import os
from contextlib import contextmanager
import shutil

import pytest

import qcodes as qc
from qcodes.dataset.sqlite.database import initialise_database, connect
from qcodes import new_experiment, new_data_set


n_experiments = 0


@pytest.fixture(scope="function")
def empty_temp_db(tmp_path):
    global n_experiments
    n_experiments = 0
    # create a temp database for testing
    try:
        qc.config["core"]["db_location"] = \
            str(tmp_path / 'temp.db')
        if os.environ.get('QCODES_SQL_DEBUG'):
            qc.config["core"]["db_debug"] = True
        else:
            qc.config["core"]["db_debug"] = False
        initialise_database()
        yield
    finally:
        # there is a very real chance that the tests will leave open
        # connections to the database. These will have gone out of scope at
        # this stage but a gc collection may not have run. The gc
        # collection ensures that all connections belonging to now out of
        # scope objects will be closed
        gc.collect()


@pytest.fixture(scope='function')
def empty_temp_db_connection(tmp_path):
    """
    Yield connection to an empty temporary DB file.
    """
    path = str(tmp_path / 'source.db')
    conn = connect(path)
    try:
        yield conn
    finally:
        conn.close()
        # there is a very real chance that the tests will leave open
        # connections to the database. These will have gone out of scope at
        # this stage but a gc collection may not have run. The gc
        # collection ensures that all connections belonging to now out of
        # scope objects will be closed
        gc.collect()


@pytest.fixture(scope='function')
def two_empty_temp_db_connections(tmp_path):
    """
    Yield connections to two empty files. Meant for use with the
    test_database_extract_runs
    """

    source_path = str(tmp_path / 'source.db')
    target_path = str(tmp_path / 'target.db')
    source_conn = connect(source_path)
    target_conn = connect(target_path)
    try:
        yield (source_conn, target_conn)
    finally:
        source_conn.close()
        target_conn.close()
        # there is a very real chance that the tests will leave open
        # connections to the database. These will have gone out of scope at
        # this stage but a gc collection may not have run. The gc
        # collection ensures that all connections belonging to now out of
        # scope objects will be closed
        gc.collect()


@pytest.fixture(scope='function')
def experiment(empty_temp_db):
    e = new_experiment("test-experiment", sample_name="test-sample")
    try:
        yield e
    finally:
        e.conn.close()


@pytest.fixture(scope='function')
def dataset(experiment):
    dataset = new_data_set("test-dataset")
    try:
        yield dataset
    finally:
        dataset.unsubscribe_all()
        dataset.conn.close()


@contextmanager
def temporarily_copied_DB(filepath: str, **kwargs):
    """
    Make a temporary copy of a db-file and delete it after use. Meant to be
    used together with the old version database fixtures, lest we change the
    fixtures on disk. Yields the connection object

    Args:
        filepath: path to the db-file

    Kwargs:
        kwargs to be passed to connect
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        dbname_new = os.path.join(tmpdir, 'temp.db')
        shutil.copy2(filepath, dbname_new)

        conn = connect(dbname_new, **kwargs)

        try:
            yield conn

        finally:
            conn.close()
