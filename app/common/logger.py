import logging

logFormatter = logging.Formatter(fmt='[%(name)s] %(levelname)-8s: %(message)s')

logger = logging.getLogger('app')
logger.setLevel(logging.DEBUG)

consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.DEBUG)
consoleHandler.setFormatter(logFormatter)

logger.addHandler(consoleHandler)
