import os
import shutil
import sys
sys.path.insert(0, os.path.abspath('..'))
from sscanss.__version import __version__


DOCS_PATH = os.path.abspath(os.path.dirname(__file__))
BUILD_PATH = os.path.join(DOCS_PATH, '_build', 'html')
WEB_PATH = os.path.join(DOCS_PATH, '_web', __version__)

if os.path.isdir(WEB_PATH):
    shutil.rmtree(WEB_PATH, ignore_errors=True)

shutil.copytree(BUILD_PATH, WEB_PATH, ignore=shutil.ignore_patterns('.buildinfo', 'objects.inv'))
