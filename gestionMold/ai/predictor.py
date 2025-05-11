# ai/predictor.py
import joblib
import os

class SalesPredictor:
    _instance = None  # Singleton instance

    @classmethod
    def instance(cls, model_path='ai/modele_entraine.pkl'):
        """
        Retourne une instance unique du prédicteur (singleton)
        """
        if cls._instance is None:
            cls._instance = cls(model_path)
        return cls._instance

    def __init__(self, model_path):
        """
        Initialise le prédicteur avec le modèle entraîné
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Le modèle n'existe pas à l'emplacement : {model_path}")
        self.model = joblib.load(model_path)

    def predict(self, input_data):
        """
        Effectue une prédiction sur les données d'entrée
        Args:
            input_data (list of float): Données pour la prédiction
        Returns:
            float: Valeur prédite
        """
        if not isinstance(input_data, (list, tuple)) or not all(isinstance(i, (int, float)) for i in input_data):
            raise ValueError("Les données d'entrée doivent être une liste ou un tuple de nombres")
        return float(self.model.predict([input_data])[0])
