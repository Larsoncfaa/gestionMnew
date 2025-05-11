# ai/predictors/inventory_predictor.py
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Union, Optional

logger = logging.getLogger(__name__)

class InventoryPredictor:
    """Prédicteur intelligent pour la gestion des stocks et réapprovisionnements"""
    
    def __init__(self, model_path: str = 'models/inventory_model.pkl'):
        """
        Initialise le prédicteur avec chargement du modèle
        
        Args:
            model_path (str): Chemin vers le modèle sauvegardé
        """
        self.model_path = Path(model_path)
        self.model = RandomForestClassifier(
            n_estimators=150,
            max_depth=5,
            random_state=42,
            class_weight='balanced'
        )
        self.features = [
            'current_stock',
            'lead_time',
            'sales_velocity',
            'seasonality_factor',
            'supplier_reliability'
        ]
        self._load_model()

    def _load_model(self) -> None:
        """Charge le modèle depuis le disque s'il existe"""
        try:
            if self.model_path.exists():
                loaded = joblib.load(self.model_path)
                self.model = loaded['model']
                self.features = loaded.get('features', self.features)
                logger.info(f"Modèle chargé depuis {self.model_path}")
        except Exception as e:
            logger.error(f"Erreur de chargement du modèle: {str(e)}")

    def save_model(self) -> None:
        """Sauvegarde le modèle et les métadonnées"""
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            to_save = {
                'model': self.model,
                'features': self.features,
                'last_trained': datetime.now().isoformat()
            }
            joblib.dump(to_save, self.model_path)
            logger.info(f"Modèle sauvegardé dans {self.model_path}")
        except Exception as e:
            logger.error(f"Erreur de sauvegarde: {str(e)}")

    def train(self, 
              inventory_data: List[Dict], 
              test_size: float = 0.2) -> Dict:
        """
        Entraîne le modèle avec des données historiques
        
        Args:
            inventory_data (List[Dict]): Données d'entraînement
            test_size (float): Proportion de données pour le test (0-1)
            
        Returns:
            Dict: Métriques de performance et statut
        """
        try:
            df = pd.DataFrame(inventory_data)
            
            # Validation des données
            required_cols = self.features + ['stockout_occurred']
            missing = set(required_cols) - set(df.columns)
            if missing:
                raise ValueError(f"Colonnes manquantes: {missing}")
            
            # Préparation des données
            X = df[self.features]
            y = df['stockout_occurred'].astype(int)
            
            # Séparation train/test
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
            
            # Entraînement
            self.model.fit(X_train, y_train)
            self.save_model()
            
            # Évaluation
            y_pred = self.model.predict(X_test)
            report = classification_report(y_test, y_pred, output_dict=True)
            
            return {
                'status': 'success',
                'accuracy': report['accuracy'],
                'precision': report['weighted avg']['precision'],
                'recall': report['weighted avg']['recall'],
                'training_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur d'entraînement: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def predict_stockout(self, 
                        product_data: Dict[str, Union[float, int]], 
                        threshold: float = 0.6) -> Dict:
        """
        Prédit le risque de rupture de stock
        
        Args:
            product_data (Dict): Caractéristiques du produit
            threshold (float): Seuil de décision (0-1)
            
        Returns:
            Dict: Résultats de prédiction avec métadonnées
        """
        try:
            # Vérification des entrées
            missing = set(self.features) - set(product_data.keys())
            if missing:
                raise ValueError(f"Données manquantes: {missing}")
            
            # Formatage des données
            X = pd.DataFrame([product_data])[self.features]
            
            # Prédiction probabiliste
            proba = self.model.predict_proba(X)[0][1]
            prediction = proba >= threshold
            
            return {
                'product_id': product_data.get('product_id', 'unknown'),
                'stockout_risk': float(proba),
                'prediction': bool(prediction),
                'threshold': threshold,
                'confidence': abs(proba - threshold),
                'timestamp': datetime.now().isoformat(),
                'model_version': self._get_version()
            }
            
        except Exception as e:
            logger.error(f"Erreur de prédiction: {str(e)}")
            return {
                'error': str(e),
                'fallback_prediction': self._fallback_prediction(product_data)
            }

    def _get_version(self) -> str:
        """Génère un identifiant de version"""
        return f"inv-predictor-v1.{datetime.now().strftime('%Y%m%d')}"

    def _fallback_prediction(self, 
                           product_data: Dict) -> Dict:
        """
        Logique de secours pour la prédiction
        
        Args:
            product_data (Dict): Données du produit
            
        Returns:
            Dict: Prédiction de secours basique
        """
        simple_risk = min(1.0, product_data.get('sales_velocity', 0) / 
                         (product_data.get('current_stock', 1) + 0.001))
        
        return {
            'stockout_risk': simple_risk,
            'prediction': simple_risk > 0.7,
            'is_fallback': True
        }

    def explain_prediction(self, 
                         product_data: Dict) -> Dict:
        """
        Explique les facteurs contribuant à la prédiction
        
        Args:
            product_data (Dict): Données du produit
            
        Returns:
            Dict: Facteurs d'influence avec leur importance
        """
        try:
            X = pd.DataFrame([product_data])[self.features]
            
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
                factors = {
                    feat: float(imp) 
                    for feat, imp in zip(self.features, importances)
                }
                
                return {
                    'product_id': product_data.get('product_id'),
                    'factors': factors,
                    'most_critical': max(factors, key=factors.get)
                }
                
            return {'warning': 'Feature importance not available'}
            
        except Exception as e:
            return {'error': str(e)}