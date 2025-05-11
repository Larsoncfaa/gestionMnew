import pandas as pd
from ai.utils.data_processing import DataProcessor

def test_clean_data():
    raw_data = [
        {"a": 1, "b": 2},
        {"a": 1, "b": 2},
        {"a": None, "b": 3},
    ]
    dp = DataProcessor()
    cleaned = dp.clean_data(raw_data)
    assert cleaned.shape[0] == 1  # une seule ligne valide

def test_normalize_features():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    dp = DataProcessor()
    result = dp.normalize_features(df.copy())
    assert result.shape == df.shape
    assert abs(result.mean().mean()) < 1e-6  # moyenne normalisée proche de 0

def test_preprocess():
    raw_data = [{"x": 1, "y": 4}, {"x": 2, "y": 5}, {"x": 3, "y": 6}]
    dp = DataProcessor()
    processed = dp.preprocess(raw_data)
    assert processed.shape == (3, 2)
