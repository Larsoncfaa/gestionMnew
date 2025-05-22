# api/utils.py

import logging
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings

logger = logging.getLogger(__name__)

def send_alert(recipient, message, link=None):
    """
    Envoie un email + crée une Notification en base.
    - recipient: CustomUser ou ClientProfile, ou liste/QuerySet de tels objets.
    - message: texte de l’alerte.
    - link: URL facultative à stocker dans la notification.
    """
    # On importe les modèles *à l’intérieur* de la fonction pour éviter la circularité
    from .models import Notification, CustomUser, ClientProfile

    # Normalisation en liste
    if isinstance(recipient, (CustomUser, ClientProfile)):
        users = [recipient]
    elif hasattr(recipient, '__iter__'):
        users = list(recipient)
    else:
        logger.warning(f"send_alert reçu un destinataire inattendu : {type(recipient)}")
        return False

    subject = '🔔 Alerte - Gestion Agricole'
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@domain.com')
    success = False

    for obj in users:
        # Résolution de l'utilisateur CustomUser
        if isinstance(obj, ClientProfile):
            user = obj.user
        elif isinstance(obj, CustomUser):
            user = obj
        else:
            logger.warning(f"Ignoré send_alert pour {obj!r} (type {type(obj)})")
            continue

        email = user.email
        if not email:
            logger.warning(f"Pas d'email pour {user!r}")
            continue

        try:
            send_mail(subject, message, from_email, [email], fail_silently=False)
            logger.info(f"Alerte envoyée par email à {email}")
            success = True
        except BadHeaderError:
            logger.error(f"En-tête invalide lors de l’envoi à {email}")
            continue
        except Exception as e:
            logger.exception(f"Erreur envoi email à {email}: {e}")
            continue

        # Création de la notification en base
        try:
            Notification.objects.create(
                user=user,
                message=message,
                link=link or ''
            )
        except Exception as e:
            logger.exception(f"Impossible de créer Notification pour {user!r}: {e}")

    return success


def generate_pdf(order):
    """
    Génère un PDF basique pour une commande.
    Retourne un django.core.files.base.ContentFile prêt à être assigné à FileField.
    """
    from io import BytesIO
    from django.core.files.base import ContentFile

    # Ici tu peux utiliser ReportLab, WeasyPrint, etc.  
    # Ce stub crée un PDF vide
    buffer = BytesIO()
    # buffer.write(b"%PDF-1.4\n%...\n")  # tu peux y écrire un vrai PDF
    buffer.seek(0)
    return ContentFile(buffer.read(), name=f"invoice_{order.id}.pdf")

def send_sms(phone_number, message):
    from twilio.rest import Client
    import re

    # Vérification basique du numéro (commence par + et chiffres, longueur raisonnable)
    if not phone_number or not re.match(r'^\+\d{8,15}$', str(phone_number)):
        # Log ou lève une exception selon ton besoin
        raise ValueError(f"Numéro de téléphone invalide : {phone_number}")

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    from_number = getattr(settings, 'TWILIO_FROM_NUMBER', None)
    if not all([account_sid, auth_token, from_number]):
        raise Exception("Twilio settings not configured")
    client = Client(account_sid, auth_token)
    client.messages.create(
        body=message,
        from_=from_number,
        to=phone_number
    )