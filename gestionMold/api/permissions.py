# api/permissions.py

from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAgriculteur(BasePermission):
    """
    Autorise uniquement les utilisateurs authentifiés avec le flag is_agriculteur.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_agriculteur)


class IsLivreur(BasePermission):
    """
    Autorise uniquement les utilisateurs authentifiés avec le flag is_livreur.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_livreur)


class IsAdminOrReadOnly(BasePermission):
    """
    Accès en lecture pour tous les authentifiés, écriture réservée aux admins.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_staff)


class IsAgriculteurOrReadOnly(BasePermission):
    """
    En lecture, tout utilisateur authentifié ; en écriture, seulement les agriculteurs.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_agriculteur)


class IsAdminOrDelivererOrOrderOwner(BasePermission):
    """
    - Les admins (is_staff) ont tous les droits.
    - En lecture (GET, HEAD, OPTIONS), seul le client propriétaire de la commande peut accéder.
    - En écriture (POST, PUT, PATCH, DELETE), seul le deliverer assigné peut modifier.
    """
    def has_permission(self, request, view):
        # Vue list/create : lecture et création (livraison) réservées aux livreurs/agrciulteurs ou admins
        if view.basename == 'delivery' and request.method == 'POST':
            # création de Delivery : seulement livreur ou admin
            return bool(request.user and (request.user.is_staff or request.user.is_livreur))
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admin full access
        if user.is_staff:
            return True

        # Lecture : le client à qui appartient la commande
        if request.method in SAFE_METHODS:
            return obj.order.client.user == user

        # Écriture : le livreur assigné
        return obj.deliverer == user
