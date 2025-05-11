# ai/predictors/delivery_predictor.py
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Union

logger = logging.getLogger(__name__)

class DeliveryPredictor:
    def __init__(self, model_path: str = 'models/delivery_model.pkl'):
        """
        Initialise le prédicteur de délais de livraison
        
        Args:
            model_path (str): Chemin vers le modèle sauvegardé
        """
        self.model_path = Path(model_path)
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            random_state=42
        )
        self._load_model()

    def _load_model(self) -> None:
        """
        Charge le modèle depuis le disque s'il existe
        """
        try:
            if self.model_path.exists():
                self.model = joblib.load(self.model_path)
                logger.info(f"Modèle chargé depuis {self.model_path}")
        except Exception as e:
            logger.error(f"Erreur de chargement du modèle: {str(e)}")
            self.model = GradientBoostingRegressor()  # Modèle par défaut

    def save_model(self) -> None:
        """
        Sauvegarde le modèle actuel sur le disque
        """
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(self.model, self.model_path)
            logger.info(f"Modèle sauvegardé dans {self.model_path}")
        except Exception as e:
            logger.error(f"Erreur de sauvegarde du modèle: {str(e)}")

    def train(self, historical_data: List[Dict]) -> Dict:
        """
        Entraîne le modèle avec les données historiques
        
        Args:
            historical_data (List[Dict]): Données d'entraînement
        
        Returns:
            Dict: Métriques d'évaluation
        """
        try:
            df = pd.DataFrame(historical_data)
            
            # Validation des données
            required_columns = {'distance', 'quantity', 'season', 'delivery_time'}
            if not required_columns.issubset(df.columns):
                raise ValueError(f"Données manquantes. Colonnes requises: {required_columns}")

            X = df[['distance', 'quantity', 'season']]
            y = df['delivery_time']
            
            self.model.fit(X, y)
            self.save_model()
            
            return {
                'status': 'success',
                'training_date': datetime.now().isoformat(),
                'model_params': self.model.get_params()
            }
            
        except Exception as e:
            logger.error(f"Erreur d'entraînement: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def predict(self, order_data: Dict) -> Dict[str, Union[float, str]]:
        """
        Prédit le temps de livraison pour une commande
        
        Args:
            order_data (Dict): Données de la commande
        
        Returns:
            Dict: Contient la prédiction et des métadonnées
        """
        try:
            # Préparation des caractéristiques
            features = {
                'distance': self._calculate_distance(order_data['client']['location']),
                'quantity': order_data['total_quantity'],
                'season': self._get_current_season()
            }
            
            # Conversion en dataframe pour la cohérence
            X = pd.DataFrame([features])
            
            # Prédiction
            prediction = self.model.predict(X)[0]
            
            return {
                'prediction': max(0, round(prediction, 2)),  # Temps ne peut pas être négatif
                'unit': 'hours',
                'model_version': self._get_model_version(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur de prédiction: {str(e)}")
            return {
                'error': str(e),
                'fallback_prediction': self._get_fallback_prediction(order_data)
            }

    @staticmethod
    def _calculate_distance(location: Dict[str, float]) -> float:
        """
        Calcule la distance depuis l'entrepôt (simplifié)
        """
        # Implémentez votre logique réelle ici
        return ((location['lat'] ** 2) + (location['lng'] ** 2)) ** 0.5

    @staticmethod
    def _get_current_season() -> int:
        """
        Détermine la saison actuelle (1-4)
        """
        month = datetime.now().month
        return (month % 12 + 3) // 3  # 1:Printemps, 2:Été, 3:Automne, 4:Hiver

    def _get_model_version(self) -> str:
        """
        Génère un identifiant de version du modèle
        """
        return f"delivery-v1.{datetime.now().strftime('%Y%m%d')}"

    def _get_fallback_prediction(self, order_data: Dict) -> float:
        """
        Fournit une estimation de secours basique
        """
        base_time = 2.0  # heures de base
        distance_factor = order_data.get('distance', 0) * 0.01
        quantity_factor = order_data.get('total_quantity', 0) * 0.05
        return round(base_time + distance_factor + quantity_factor, 2)