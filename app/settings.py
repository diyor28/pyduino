import os

BASE_DIR = os.getcwd()
DOWNLOADS_DIR = 'downloads'
DEBUG = os.environ.get('DEBUG', False)
# DEBUG = False
RTD_A = 3.9083e-3
RTD_B = - 5.775e-7
BAUD_RATE = 250_000
MAX_FAILED_ATTEMPTS = 4
RETRY_IN = 10
