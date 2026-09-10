"""Keep all test application imports away from the user's running data store."""
import os
import tempfile
_test_state = tempfile.TemporaryDirectory(prefix='loopcheck-unit-state-')
os.environ['LOOPCHECK_DATA'] = _test_state.name
