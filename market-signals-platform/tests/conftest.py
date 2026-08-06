import os
import tempfile

_tmpdir = tempfile.mkdtemp(prefix="msp-test-")
os.environ["MSP_DATA_DIR"] = _tmpdir
os.environ["MSP_DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
