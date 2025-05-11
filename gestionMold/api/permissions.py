from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAgriculteur(BasePermission):
    """
    Permission pour restreindre l'accès aux seuls utilisateurs ayant le rôle 'agriculteur'.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'is_agriculteur', False)


class IsAdminOrDelivererOrOrderOwner(BasePermission):
    """
    Permission complexe :
    - L'admin a tous les droits.
    - En lecture (GET, HEAD, OPTIONS), le client ayant passé la commande peut accéder.
    - En écriture, seul le livreur assigné peut modifier l'objet Delivery.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user.is_authenticated:
            return False

        # Accès total pour les admins
        if user.is_staff:
            return True

        # Lecture : seul le client propriétaire de la commande
        if request.method in SAFE_METHODS:
            return getattr(obj.order.client, 'user', None) == user

        # Écriture : seul le livreur assigné
        return obj.deliverer == user
