# ai/utils/data_preprocessor.py
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Dict, List, Union, Optional

logger = logging.getLogger(__name__)

class DataPreprocessor:
    """Classe pour le prétraitement des données avant analyse ou entraînement de modèles"""

    @staticmethod
    def preprocess_sales_data(raw_data: Union[List[Dict], pd.DataFrame]) -> pd.DataFrame:
        """
        Nettoie et transforme les données de ventes
        
        Args:
            raw_data: Données brutes (liste de dict ou DataFrame)
            
        Returns:
            pd.DataFrame: Données nettoyées et transformées
        """
        try:
            # Conversion en DataFrame si nécessaire
            df = raw_data if isinstance(raw_data, pd.DataFrame) else pd.DataFrame(raw_data)
            
            # Validation des colonnes requises
            required_columns = {'date', 'product_id', 'quantity', 'price'}
            missing_cols = required_columns - set(df.columns)
            if missing_cols:
                raise ValueError(f"Colonnes manquantes: {missing_cols}")

            # 1. Nettoyage des données
            processed_data = (
                df
                # Suppression des lignes avec valeurs manquantes critiques
                .dropna(subset=['product_id', 'quantity'])
                # Conversion des types
                .assign(
                    date=lambda x: pd.to_datetime(x['date']),
                    quantity=lambda x: pd.to_numeric(x['quantity']),
                    price=lambda x: pd.to_numeric(x['price'].replace('[\$,]', '', regex=True))
                )
                # Filtrage des valeurs aberrantes
                .query('quantity > 0 and price > 0')
                # Ajout de caractéristiques dérivées
                .assign(
                    day_of_week=lambda x: x['date'].dt.dayofweek,
                    month=lambda x: x['date'].dt.month,
                    revenue=lambda x: x['quantity'] * x['price']
                )
            )

            # 2. Agrégations si nécessaire
            processed_data = processed_data.groupby(['date', 'product_id']).agg({
                'quantity': 'sum',
                'price': 'mean',
                'revenue': 'sum',
                'day_of_week': 'first',
                'month': 'first'
            }).reset_index()

            logger.info(f"Données de ventes prétraitées. Shape: {processed_data.shape}")
            return processed_data

        except Exception as e:
            logger.error(f"Erreur de prétraitement: {str(e)}")
            raise ValueError(f"Échec du prétraitement: {str(e)}")

    @staticmethod
    def preprocess_inventory_data(raw_data: Union[List[Dict], pd.DataFrame]) -> pd.DataFrame:
        """
        Prétraite les données d'inventaire pour l'analyse
        
        Args:
            raw_data: Données brutes d'inventaire
            
        Returns:
            pd.DataFrame: Données d'inventaire nettoyées
        """
        try:
            df = raw_data if isinstance(raw_data, pd.DataFrame) else pd.DataFrame(raw_data)
            
            required_cols = {'product_id', 'current_stock', 'lead_time', 'supplier_id'}
            missing_cols = required_cols - set(df.columns)
            if missing_cols:
                raise ValueError(f"Colonnes d'inventaire manquantes: {missing_cols}")

            processed_data = (
                df
                .dropna(subset=['product_id', 'current_stock'])
                .assign(
                    current_stock=lambda x: pd.to_numeric(x['current_stock']),
                    lead_time=lambda x: pd.to_numeric(x['lead_time'].fillna(7)),  # Valeur par défaut 7 jours
                    is_low_stock=lambda x: (x['current_stock'] < x['lead_time'] * 2).astype(int)
                )
                .sort_values('product_id')
            )
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Erreur de prétraitement inventaire: {str(e)}")
            raise

    @staticmethod
    def add_temporal_features(df: pd.DataFrame, date_col: str = 'date') -> pd.DataFrame:
        """
        Ajoute des caractéristiques temporelles à un DataFrame
        
        Args:
            df: DataFrame contenant une colonne de dates
            date_col: Nom de la colonne de date
            
        Returns:
            DataFrame avec caractéristiques temporelles ajoutées
        """
        df[date_col] = pd.to_datetime(df[date_col])
        return df.assign(
            day_of_week=lambda x: x[date_col].dt.dayofweek,
            month=lambda x: x[date_col].dt.month,
            quarter=lambda x: x[date_col].dt.quarter,
            year=lambda x: x[date_col].dt.year,
            day_of_year=lambda x: x[date_col].dt.dayofyear,
            is_weekend=lambda x: x[date_col].dt.dayofweek >= 5
        )