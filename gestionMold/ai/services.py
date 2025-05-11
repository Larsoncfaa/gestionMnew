from django.core.cache import cache
from django.conf import settings
from .predictors.delivery_predictor import DeliveryPredictor
from .predictors.inventory_predictor import InventoryPredictor
from .predictors.sales_predictor import SalesPredictor

def _cached(key, fn, *args):
    res = cache.get(key)
    if res is None:
        res = fn(*args)
        cache.set(key, res, 3600)
    return res

def predict_delivery(data):
    key = f"delivery:{data}"
    return _cached(key, DeliveryPredictor.instance(settings.DELIVERY_MODEL_PATH).predict, data)

def predict_inventory(data):
    key = f"inventory:{data.get('product_id')}"
    return _cached(key, InventoryPredictor.instance(settings.INVENTORY_MODEL_PATH).predict_stockout, data)

def predict_sales(data):
    key = f"sales:{tuple(data.items())}"
    return _cached(key, SalesPredictor.instance(settings.SALES_MODEL_PATH).predict, data)
