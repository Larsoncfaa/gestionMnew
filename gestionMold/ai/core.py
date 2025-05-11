import numpy as np

def predict_from_input(product_id, quantity):
    # Exemple : prédiction basée sur une règle simple
    quantity = float(quantity)
    
    # Exemple : règle simple pour illustrer
    if quantity > 100:
        return "Prévoir un réapprovisionnement"
    else:
        return "Stock suffisant"
