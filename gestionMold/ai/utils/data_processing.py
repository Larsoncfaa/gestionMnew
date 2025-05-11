# ai/utils/data_processing.py
import pandas as pd
from sklearn.preprocessing import StandardScaler

class DataProcessor:
    def __init__(self):
        self.scaler = StandardScaler()
    
    def clean_data(self, raw_data):
        """Nettoie les données brutes"""
        df = pd.DataFrame(raw_data)
        df = df.dropna()
        df = df.drop_duplicates()
        return df
    
    def normalize_features(self, df):
        """Normalise les caractéristiques"""
        numeric_cols = df.select_dtypes(include=['number']).columns
        df[numeric_cols] = self.scaler.fit_transform(df[numeric_cols])
        return df

    def preprocess(self, raw_data):
        """Pipeline complet de prétraitement"""
        df = self.clean_data(raw_data)
        df = self.normalize_features(df)
        return df.values