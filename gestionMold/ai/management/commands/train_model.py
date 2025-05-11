import os
from django.conf import settings
from django.core.management.base import BaseCommand
from sklearn.ensemble import RandomForestRegressor
import joblib

class Command(BaseCommand):
    help = 'Entraîne le modèle de prédiction'

    def handle(self, *args, **options):
        try:
            # Créer le répertoire si inexistant
            model_dir = os.path.join(settings.BASE_DIR, 'ai', 'models')
            os.makedirs(model_dir, exist_ok=True)
            
            self.stdout.write("Entraînement du modèle...")
            
            # 1. Données d'exemple
            X = [[1], [2], [3]]
            y = [1, 2, 3]
            
            # 2. Entraînement
            model = RandomForestRegressor()
            model.fit(X, y)
            
            # 3. Chemin complet
            model_path = os.path.join(model_dir, 'basic_model.pkl')
            joblib.dump(model, model_path)
            
            self.stdout.write(
                self.style.SUCCESS(f"Modèle sauvegardé dans : {model_path}")
            )
            
        except Exception as e:
            self.stderr.write(f"Erreur : {str(e)}")