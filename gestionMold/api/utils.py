from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_alert(recipient, message):
    """
    Envoie un email d'alerte à l'utilisateur (agriculteur, client, etc.).
    """
    email = getattr(recipient, 'email', None)
    if not email:
        logger.warning(f"Aucun email défini pour le destinataire : {recipient}")
        return False

    subject = '🔔 Alerte - Gestion Agricole'
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@domain.com')

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"Alerte envoyée à {email}")
        return True

    except BadHeaderError:
        logger.error(f"En-tête invalide lors de l’envoi d’alerte à {email}")
    except Exception as e:
        logger.exception(f"Erreur lors de l’envoi de l’email à {email} : {e}")

    return False
