import pandas as pd
import pytest
from ai.utils.data_preprocessor import DataPreprocessor

# Données de test
sales_data = [
    {"date": "2024-01-01", "product_id": "P1", "quantity": 2, "price": "$10"},
    {"date": "2024-01-01", "product_id": "P1", "quantity": 3, "price": "$15"},
    {"date": "2024-01-02", "product_id": "P2", "quantity": 1, "price": "$20"},
]

inventory_data = [
    {"product_id": "P1", "current_stock": 10, "lead_time": 3, "supplier_id": "S1"},
    {"product_id": "P2", "current_stock": 2, "lead_time": 5, "supplier_id": "S2"},
]

def test_preprocess_sales_data():
    df = DataPreprocessor.preprocess_sales_data(sales_data)
    assert not df.empty
    assert set(df.columns) == {'date', 'product_id', 'quantity', 'price', 'revenue', 'day_of_week', 'month'}

def test_missing_column_sales_data():
    incomplete_data = [{"product_id": "P1", "quantity": 2, "price": "$10"}]
    with pytest.raises(ValueError):
        DataPreprocessor.preprocess_sales_data(incomplete_data)

def test_preprocess_inventory_data():
    df = DataPreprocessor.preprocess_inventory_data(inventory_data)
    assert "is_low_stock" in df.columns
    assert df["is_low_stock"].isin([0, 1]).all()

def test_add_temporal_features():
    df = pd.DataFrame({"date": ["2024-01-01", "2024-04-15"]})
    result = DataPreprocessor.add_temporal_features(df)
    expected_cols = {"day_of_week", "month", "quarter", "year", "day_of_year", "is_weekend"}
    assert expected_cols.issubset(set(result.columns))
