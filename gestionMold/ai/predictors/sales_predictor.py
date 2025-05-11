# ai/predictors/sales_predictor.py
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SalesPredictor:
    def __init__(self, model_path='models/sales_model.pkl'):
        """
        Initialise le prédicteur avec chargement du modèle
        """
        self.model_path = Path(model_path)
        self.model = None
        self.scaler = None
        self.load_model()
        
        # Configuration par défaut
        self.min_confidence = 0.7
        self.last_retrain_date = None

    def load_model(self):
        """
        Charge le modèle et le scaler depuis le disque
        """
        try:
            artifacts = joblib.load(self.model_path)
            self.model = artifacts['model']
            self.scaler = artifacts['scaler']
            self.last_retrain_date = artifacts.get('training_date')
            logger.info(f"Modèle chargé depuis {self.model_path}")
        except Exception as e:
            logger.error(f"Erreur de chargement du modèle: {str(e)}")
            self.initialize_default_model()

    def initialize_default_model(self):
        """
        Initialise un modèle par défaut si le chargement échoue
        """
        logger.warning("Initialisation d'un modèle par défaut")
        self.model = RandomForestRegressor(n_estimators=100)
        self.scaler = StandardScaler()
        self.last_retrain_date = datetime.now().isoformat()

    def preprocess_input(self, data):
        """
        Prétraite les données d'entrée
        """
        # Conversion en tableau numpy et normalisation
        features = np.array([
            data['historique_ventes'],
            data['stock_disponible'],
            data['saison'],
            data['prix'],
            data['promotion']
        ]).reshape(1, -1)
        
        return self.scaler.transform(features)

    def predict(self, input_data):
        """
        Effectue une prédiction avec gestion d'erreur
        """
        try:
            # Préparation des données
            processed_data = self.preprocess_input(input_data)
            
            # Prédiction
            prediction = self.model.predict(processed_data)[0]
            confidence = self.calculate_confidence(processed_data)
            
            # Post-traitement
            prediction = max(0, prediction)  # Les ventes ne peuvent pas être négatives
            
            return {
                'prediction': round(prediction, 2),
                'confidence': round(confidence, 2),
                'model_version': self.get_model_version(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur de prédiction: {str(e)}")
            return {
                'error': str(e),
                'fallback_prediction': self.generate_fallback_prediction(input_data)
            }

    def calculate_confidence(self, input_data):
        """
        Calcule la confiance de la prédiction
        """
        # Ici vous pourriez implémenter une vraie métrique de confiance
        return max(self.min_confidence, 
                1 - abs(input_data[0][0] - input_data[0][1]) / 100)

    def get_model_version(self):
        """
        Retourne la version du modèle basée sur la date d'entraînement
        """
        if self.last_retrain_date:
            return f"1.0.{self.last_retrain_date[:10].replace('-', '')}"
        return "1.0.0"

    def generate_fallback_prediction(self, input_data):
        """
        Génère une prédiction de secours simple
        """
        return round(input_data['historique_ventes'] * 0.8, 2)

    def save_model(self, path=None):
        """
        Sauvegarde le modèle actuel
        """
        save_path = Path(path) if path else self.model_path
        save_path.parent.mkdir(exist_ok=True)
        
        artifacts = {
            'model': self.model,
            'scaler': self.scaler,
            'training_date': datetime.now().isoformat(),
            'metadata': {
                'model_type': 'RandomForestRegressor',
                'features': ['historique_ventes', 'stock_disponible', 'saison', 'prix', 'promotion']
            }
        }
        
        joblib.dump(artifacts, save_path)
        logger.info(f"Modèle sauvegardé dans {save_path}")