import logging
logger = logging.getLogger('ai')
logger.setLevel(logging.INFO)
handler=logging.FileHandler('ai/logs/predictions.log')
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logger.addHandler(handler)
