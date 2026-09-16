import json
import errno
import os
import pty
import re
import select
import signal
import time
from pathlib import Path
import shutil
from test_dots import Fixture, SOURCE


class Installer(Fixture):
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory(prefix="dots test ")
