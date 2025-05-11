import logging
from ai.utils import logger as custom_logger

def test_logger_configuration():
    log = custom_logger.logger
    assert isinstance(log, logging.Logger)
    assert log.level == logging.INFO
    assert any(isinstance(h, logging.FileHandler) for h in log.handlers)
