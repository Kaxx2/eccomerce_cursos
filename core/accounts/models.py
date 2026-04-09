from django.db import models
from django.contrib.auth.models import User


class Empresa(models.Model):
    nombre = models.CharField(max_length=255)
    creada_en = models.DateTimeField(auto_now_add=True)
    codigo_sap = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True
    )

     # 👇 RELACIÓN PADRE
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='divisiones'
    )


    def __str__(self):
        return self.nombre


class UserProfile(models.Model):
    USER_TYPES = (
        ('ADMIN_EMPRESA', 'Admin Empresa'),
        ('EMPLEADO', 'Empleado'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    empresa = models.ForeignKey(
    Empresa,
    on_delete=models.SET_NULL,
    null=True,
    blank=True
)
    
    nacionalidad = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )


    tipo = models.CharField(max_length=20, choices=USER_TYPES, null=True, blank=True)

    def __str__(self):
        nombre = f"{self.user.first_name} {self.user.last_name}".strip()
        return f"{nombre or self.user.username} ({self.get_tipo_display()})"
    
    def save(self, *args, **kwargs):
        from .models import Wallet, CreditTransaction

        if self.pk:
            old = UserProfile.objects.get(pk=self.pk)

            # 👇 detectamos que salió de una empresa
            if old.empresa and not self.empresa:

                wallet_user = Wallet.objects.filter(user=self.user).first()
                wallet_empresa = Wallet.objects.filter(empresa=old.empresa).first()

                # ✅ SOLO créditos de empresa
                if wallet_user and wallet_empresa and wallet_user.balance_empresa > 0:
                    amount = wallet_user.balance_empresa

                    # quitar créditos de empresa al usuario
                    wallet_user.balance_empresa = 0
                    wallet_user.save()

                    # devolver a empresa
                    wallet_empresa.balance_empresa += amount
                    wallet_empresa.save()

                    # 👇 registrar devolución
                    CreditTransaction.objects.create(
                        wallet=wallet_empresa,
                        amount=amount,
                        transaction_type="refund_empresa",
                        created_by=request.user,
                    )

                    CreditTransaction.objects.create(
                        wallet=wallet_user,
                        amount=-amount,
                        transaction_type="refund_empresa",
                        created_by=request.user,
                    )

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Gestión de perfil"
        verbose_name_plural = "Gestión de perfiles"


class Wallet(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    balance_empresa = models.PositiveIntegerField(default=0)
    balance_personal = models.PositiveIntegerField(default=0)

    def owner(self):
        return self.user if self.user else self.empresa

    @property
    def balance_total(self):
        return self.balance_empresa + self.balance_personal

    def __str__(self):
        owner = self.owner()
        return f"{owner} - {self.balance_total} créditos"

class CreditTransaction(models.Model):

    TRANSACTION_TYPES = (
        ("purchase_empresa", "Compra empresarial"),
        ("purchase_personal", "Compra particular"),
        
        ("transfer", "Transferencia"),
        ("redeem", "Consumo"),
        ("refund_empresa", "Devolución automática"),
        ("adjustment", "Ajuste Manual"),
    )

    from django.contrib.auth.models import User

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    amount = models.IntegerField()
    reverted = models.BooleanField(default=False)

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )

    # 👇 NUEVO
    motivo = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet.owner()} | {self.amount} | {self.get_transaction_type_display()} | {self.motivo or '-'}"

    class Meta:
        verbose_name = "Historial de transacción"
        verbose_name_plural = "Historial de transacciones"
    
class CreditTransfer(models.Model):

    from_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="sent_transfers"
    )

    to_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="received_transfers"
    )

    amount = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_wallet} → {self.to_wallet} ({self.amount})"
    

class Equipo(models.Model):
    nombre = models.CharField(max_length=255)
    creditos = models.IntegerField()

    def __str__(self):
        return self.nombre
    

class Curso(models.Model):
    nombre = models.CharField(max_length=255)
    creditos = models.IntegerField()

    def __str__(self):
        return f"{self.nombre} ({self.creditos} créditos)"