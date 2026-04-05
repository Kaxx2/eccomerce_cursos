from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Wallet, UserProfile


# ✅ Crear wallet automáticamente cuando se crea usuario


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if not created:
        return

    # ❌ NO crear wallet para admins
    if instance.is_staff or instance.is_superuser:
        return

    print("SE CREÓ USUARIO NORMAL")  # debug opcional

    Wallet.objects.get_or_create(user=instance)


# ✅ Crear wallet automáticamente cuando se crea empresa (opcional pero bueno)
from .models import Empresa

@receiver(post_save, sender=Empresa)
def create_empresa_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(empresa=instance)