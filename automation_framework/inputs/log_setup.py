import logging

import time

# Define TRACE level (numerically lower than DEBUG)
TRACE_LEVEL_NUM = 5
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")

# Add trace() method to Logger class
def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE_LEVEL_NUM):
        self._log(TRACE_LEVEL_NUM, message, args, **kwargs)

logging.Logger.trace = trace

class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Level first character: e.g., I for INFO, D for DEBUG
        levelchar = record.levelname[0]

        # Timestamp in MMDD HH:MM:SS.sss format
        timestamp = time.strftime("%m%d %H:%M:%S", time.localtime(record.created))
        millis = int(record.msecs)
        timestamp += f".{millis:03d}"

        # Filename:lineno
        location = f"{record.name}:{record.lineno}"

        # Compose message
        formatted = f"{levelchar}{timestamp} {location}] {record.getMessage()}"
        return formatted


def setup_logger(verbose):
    handler = logging.StreamHandler()
    handler.setFormatter(CustomFormatter())

    if verbose == 0:
        level = logging.INFO
    elif verbose == 1:
        level = logging.DEBUG
    else:  # verbosity == 2
        level = TRACE_LEVEL_NUM

    logging.basicConfig(level=level, handlers=[handler])

    logging.getLogger("setup_logger").info(f"Logging level set to {logging.getLevelName(level)}")