import logging
from textual.logging import TextualHandler

logFormatter = logging.Formatter(fmt='[%(name)s] %(levelname)-8s: %(message)s')

logger = logging.getLogger('app')
logger.setLevel(logging.DEBUG)

consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.DEBUG)
consoleHandler.setFormatter(logFormatter)

textualHandler = TextualHandler()

logger.addHandler(consoleHandler)
logger.addHandler(textualHandler)
