import os

BASE_DIR = os.getcwd()
DOWNLOADS_DIR = 'downloads'
VERBOSE = int(os.environ.get('VERBOSE', 0))
RTD_A = 3.9083e-3
RTD_B = - 5.775e-7
BAUD_RATE = 250_000
MAX_FAILED_ATTEMPTS = 4
RETRY_IN = 10


def log(*args, verbose=1):
	if verbose <= VERBOSE:
		print(*args)
