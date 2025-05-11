import joblib
from pathlib import Path

class BasePredictor:
    _instances = {}
    @classmethod
    def instance(cls, model_path):
        if cls not in cls._instances:
            cls._instances[cls] = cls(model_path)
        return cls._instances[cls]
    def __init__(self, model_path):
        self.model_path = Path(model_path)
        # loaded in subclass
