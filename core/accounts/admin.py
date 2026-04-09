from django.contrib import admin
from .models import Empresa, Wallet, UserProfile, CreditTransaction, CreditTransfer
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.urls import path, reverse

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from django.contrib import admin
from django.contrib.auth.models import Group

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from .models import Empresa, UserProfile, Wallet, CreditTransaction
from .models import Equipo, Curso

from accounts.models import Curso

admin.site.unregister(Group)

admin.site.site_header = "Panel de Administración - Analytical Technologies"
admin.site.site_title = "Analytical Technologies"
admin.site.index_title = "Training Credits - AdminCenter"



class CustomAdminSite(AdminSite):
    site_header = "Analytical Technologies"
    site_title = "Admin"
    index_title = "Centro de administración - Training Credits"

    def index(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}

        from django.db.models import Sum

        # KPIs reales
        total_empresas = Empresa.objects.count()
        total_users = UserProfile.objects.count()

        totales = Wallet.objects.aggregate(
            total_empresa=Sum("balance_empresa"),
            total_personal=Sum("balance_personal")
        )

        total_creditos = (totales["total_empresa"] or 0) + (totales["total_personal"] or 0)

        extra_context.update({
            "total_empresas": total_empresas,
            "total_users": total_users,
            "total_creditos": total_creditos,
        })

        return super().index(request, extra_context)
    
    def get_urls(self):
            urls = super().get_urls()

            custom_urls = [
                path('ajuste-manual/', self.admin_view(ajuste_manual_global)),
            ]

            return custom_urls + urls
    


#class EmpresaUsuarioFilter(admin.SimpleListFilter):
    #title = "Tipo"
    #parameter_name = "tipo"

    #def lookups(self, request, model_admin):
        #return (
           # ("empresa", "Empresas"),
            #("usuarios", "Usuarios sin empresa"),
        #)

    #def queryset(self, request, queryset):
      #  if self.value() == "empresa":
          #  return queryset.filter(empresa__isnull=False)
      #  if self.value() == "usuarios":
         #   return queryset.filter(empresa__isnull=True)
       # return queryset 

class UserProfileInline(admin.TabularInline):
    model = UserProfile
    extra = 0
    can_delete = False
    show_change_link = False

    fields = ("user", "tipo", "creditos")
    readonly_fields = ("user", "tipo", "creditos")

    def creditos(self, obj):
        if obj.user:
            wallet = Wallet.objects.filter(user=obj.user).first()
            return wallet.balance if wallet else 0
        return 0

    creditos.short_description = "Créditos"

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'creada_en', 'creditos', 'transferir_creditos', 'cargar_creditos', 'parent')


    fields = ('nombre', 'parent')  # 👈 muestra selector
    inlines = [UserProfileInline]

    

    def has_change_permission(self, request, obj=None):
        return False

    def creditos(self, obj):
        wallet = Wallet.objects.filter(empresa=obj).first()
        return getattr(wallet, "balance_empresa", 0)
    creditos.short_description = "Créditos"

    def transferir_creditos(self, obj):
        url = reverse("admin:transferir-creditos", args=[obj.id])
        return format_html(
            '<a class="button" style="padding:4px 8px; background:#417690; color:white; border-radius:4px;" href="{}">Transferir</a>',
            url
    )

    def cargar_creditos(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html

        url = reverse("admin:cargar-creditos", args=[obj.id])
        return format_html(
            '<a class="button" style="padding:4px 8px; background:#28a745; color:white; border-radius:4px;" href="{}">Cargar</a>',
            url
        )

    cargar_creditos.short_description = "Cargar créditos"

    def cargar_creditos_view(self, request, empresa_id):

        from django.shortcuts import get_object_or_404, render, redirect
        from django.contrib import messages

        empresa = get_object_or_404(Empresa, id=empresa_id)

        wallet_empresa, _ = Wallet.objects.get_or_create(
            empresa=empresa,
            defaults={
                "balance_empresa": 0,
                "balance_personal": 0
            }
        )

        if request.method == "POST":
            try:
                amount = int(request.POST.get("amount"))
                if amount <= 0:
                    raise ValueError
            except:
                messages.error(request, "Monto inválido")
                return redirect(request.path)

            # 🔥 NUEVO SISTEMA DE MOTIVO
            motivo_select = request.POST.get("motivo_select", "").strip()
            motivo_custom = request.POST.get("motivo_custom", "").strip()

            # lógica clara
            if motivo_select == "otro":
                motivo = motivo_custom
            elif motivo_select:
                motivo = motivo_select
            else:
                motivo = ""

            # validación final
            if not motivo:
                messages.error(request, "Debés ingresar un motivo")
                return redirect(request.path)

            # ✅ sumar créditos de empresa
            wallet_empresa.balance_empresa += amount
            wallet_empresa.save()

            # ✅ historial
            CreditTransaction.objects.create(
                wallet=wallet_empresa,
                amount=amount,
                transaction_type="purchase_empresa",  # 👈 mantené consistente
                motivo=motivo,
                created_by=request.user
            )

            messages.success(request, "Créditos cargados correctamente")
            return redirect("/admin/accounts/empresa/")

        context = {
            "empresa": empresa,
            "wallet": wallet_empresa,
        }

        return render(request, "cargar_creditos.html", context)
        
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'transferir-creditos/<int:empresa_id>/',
                self.admin_site.admin_view(self.transferir_creditos_view),
                name="transferir-creditos",
            ),
            path(
                'cargar-creditos/<int:empresa_id>/',
                self.admin_site.admin_view(self.cargar_creditos_view),
                name="cargar-creditos",
            ),
        ]
        return custom_urls + urls
    
    def transferir_creditos_view(self, request, empresa_id):

        from django.shortcuts import get_object_or_404, render, redirect
        from django.contrib import messages

        empresa = get_object_or_404(Empresa, id=empresa_id)

        wallet_empresa, _ = Wallet.objects.get_or_create(
            empresa=empresa,
            defaults={"balance_empresa": 0, "balance_personal": 0}
        )

        usuarios = User.objects.filter(userprofile__empresa=empresa)

        if request.method == "POST":

            user_id = request.POST.get("user")

            if not user_id:
                messages.error(request, "Seleccioná un usuario")
                return redirect(request.path)

            # monto
            try:
                amount = int(request.POST.get("amount"))
                if amount <= 0:
                    raise ValueError
            except:
                messages.error(request, "Monto inválido")
                return redirect(request.path)

            # 🔥 MOTIVO NUEVO
            motivo_select = request.POST.get("motivo_select", "").strip()
            motivo_custom = request.POST.get("motivo_custom", "").strip()

            if motivo_select == "otro":
                motivo = motivo_custom
            elif motivo_select:
                motivo = motivo_select
            else:
                motivo = ""

            if not motivo:
                messages.error(request, "Debés ingresar un motivo")
                return redirect(request.path)

            user = get_object_or_404(User, id=user_id)
            profile = getattr(user, 'userprofile', None)

            if not profile or not profile.empresa:
                messages.error(request, "El usuario no pertenece a una empresa")
                return redirect(request.path)

            wallet_user, _ = Wallet.objects.get_or_create(
                user=user,
                defaults={"balance_empresa": 0, "balance_personal": 0}
            )

            if wallet_empresa.balance_empresa < amount:
                messages.error(request, "La empresa no tiene suficientes créditos")
            else:
                # transferencia
                wallet_empresa.balance_empresa -= amount
                wallet_user.balance_empresa += amount

                wallet_empresa.save()
                wallet_user.save()

                # registro transferencia
                CreditTransfer.objects.create(
                    from_wallet=wallet_empresa,
                    to_wallet=wallet_user,
                    amount=amount
                )

                # historial empresa
                CreditTransaction.objects.create(
                    wallet=wallet_empresa,
                    amount=-amount,
                    transaction_type="transfer",
                    motivo=f"Transferencia a {user.username} - {motivo}",
                    created_by=request.user
                )

                # historial usuario
                CreditTransaction.objects.create(
                    wallet=wallet_user,
                    amount=amount,
                    transaction_type="transfer",
                    motivo=f"Transferencia desde {empresa.nombre} - {motivo}",
                    created_by=request.user
                )

                messages.success(request, "Transferencia realizada")
                return redirect("/admin/accounts/empresa/")

        context = {
            "empresa": empresa,
            "wallet": wallet_empresa,
            "usuarios": usuarios
        }

        return render(request, "transferir_creditos.html", context)
    

admin.site.unregister(User)
@admin.register(User)
class UserAdmin(BaseUserAdmin):

    list_display = ("username", "first_name", "last_name", "email")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Información personal", {"fields": ("first_name", "last_name", "email")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2", "first_name", "last_name", "email"),
        }),
    )

@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = (
    'wallet',
    'amount',
    'colored_transaction_type',
    'motivo',
    'created_by',  # 👈 nuevo
    'created_at'
)
    list_filter = ("transaction_type",)
    readonly_fields = ("wallet", "amount", "transaction_type", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
    def colored_transaction_type(self, obj):
        label = obj.get_transaction_type_display()

        if obj.transaction_type in ["adjustment", "refund_empresa", "transfer"]:
            color = "#ffc107"  # amarillo

        elif obj.transaction_type in ["purchase", "purchase_personal", "purchase_empresa"]:
            color = "#28a745"  # verde

        elif obj.transaction_type == "redeem":
            color = "#dc3545"  # rojo

        else:
            color = "#ccc"  # fallback

        return format_html(
            '<strong style="color:{};">{}</strong>',
            color,
            label.upper()
        )

    colored_transaction_type.short_description = "Transaction type"
    
    
    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()

    
        return urls
    
#@admin.register(CreditTransfer)
#class CreditTransferAdmin(admin.ModelAdmin):
   #list_display = ("from_wallet", "to_wallet", "amount", "created_at")



@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = ('user', 'tipo', 'empresa', 'nacionalidad')
    list_filter = ('tipo', 'empresa')
    search_fields = ('user__username',)
from django.contrib import admin

class WalletTypeFilter(admin.SimpleListFilter):
    title = 'Tipo de wallet'
    parameter_name = 'tipo_wallet'

    def lookups(self, request, model_admin):
        return (
            ('empresa', 'Empresa'),
            ('usuario', 'Usuario'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'empresa':
            return queryset.filter(empresa__isnull=False)
        if self.value() == 'usuario':
            return queryset.filter(user__isnull=False)
        return queryset
    

class WalletAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
    
    def cargar_creditos(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html

        # ❌ empresas NO (ya lo hacés desde EmpresaAdmin)
        if obj.empresa:
            return "-"

        url = reverse("admin:cargar-creditos-wallet", args=[obj.id])

        return format_html(
            '<a class="button" style="padding:4px 8px; background:#28a745; color:white; border-radius:4px;" href="{}">Cargar créditos</a>',
            url
        )

    cargar_creditos.short_description = "Acción"
        
    def canjear_creditos(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html

        # ❌ empresas no pueden canjear
        if obj.empresa:
            return "-"

        # ✅ usar balance total (empresa + personal)
        if obj.balance_total <= 0:
            return "Sin saldo"

        url = reverse("admin:canjear-creditos", args=[obj.id])

        return format_html(
            '<a class="button" style="padding:4px 8px; background:#dc3545; color:white; border-radius:4px;" href="{}">Canjear curso</a>',
            url
        )

    canjear_creditos.short_description = "Acción"

    def cargar_creditos_wallet_view(self, request, wallet_id):
        from django.shortcuts import get_object_or_404, render, redirect
        from django.contrib import messages

        wallet = get_object_or_404(Wallet, id=wallet_id)

        # ❌ empresas no usan esta view
        if wallet.empresa:
            messages.error(request, "Esta acción es solo para usuarios")
            return redirect("/admin/accounts/wallet/")

        if request.method == "POST":
            try:
                amount = int(request.POST.get("amount"))
                if amount <= 0:
                    raise ValueError
            except:
                messages.error(request, "Monto inválido")
                return redirect(request.path)

            # 🔥 NUEVO SISTEMA DE MOTIVO
            motivo_select = request.POST.get("motivo_select", "").strip()
            motivo_custom = request.POST.get("motivo_custom", "").strip()

            if motivo_select == "otro":
                motivo = motivo_custom
            elif motivo_select:
                motivo = motivo_select
            else:
                motivo = ""

            if not motivo:
                messages.error(request, "Debés ingresar un motivo")
                return redirect(request.path)

            # ✅ créditos personales
            wallet.balance_personal += amount
            wallet.save()

            # ✅ historial
            CreditTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type="purchase_personal",
                motivo=motivo,
                created_by=request.user
            )

            messages.success(request, "Créditos cargados correctamente")
            return redirect("/admin/accounts/wallet/")

        context = {
            "wallet": wallet,
        }

        return render(request, "cargar_creditos_wallet.html", context)

    def canjear_creditos_view(self, request, wallet_id):
        from django.shortcuts import get_object_or_404, render, redirect
        from django.contrib import messages

        wallet = get_object_or_404(Wallet, id=wallet_id)

        if wallet.empresa:
            messages.error(request, "Las empresas no pueden canjear créditos")
            return redirect("/admin/accounts/wallet/")

        if request.method == "POST":
            curso_id = request.POST.get("curso_id")

            try:
                curso = Curso.objects.get(id=curso_id)
            except Curso.DoesNotExist:
                messages.error(request, "Curso inválido")
                return redirect(request.path)

            total_disponible = wallet.balance_empresa + wallet.balance_personal

            # ✅ validación correcta
            if total_disponible < curso.creditos:
                messages.error(request, "Fondos insuficientes")
            else:
                costo = curso.creditos

                # 🔥 consumir empresa primero
                if wallet.balance_empresa >= costo:
                    wallet.balance_empresa -= costo
                else:
                    restante = costo - wallet.balance_empresa
                    wallet.balance_empresa = 0
                    wallet.balance_personal -= restante

                wallet.save()

                # ✅ historial (podrías mejorar tipo si querés)
                CreditTransaction.objects.create(
                    wallet=wallet,
                    amount=-costo,  # 👈 negativo porque consume
                    transaction_type="redeem",
                    motivo="Canje por curso",
                    created_by=request.user
                )

                messages.success(request, "Curso canjeado correctamente")
                return redirect("/admin/accounts/wallet/")

        context = {
            "wallet": wallet,
            "cursos": Curso.objects.all(),
        }

        return render(request, "canjear_creditos.html", context)
    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path(
                'canjear-creditos/<int:wallet_id>/',
                self.admin_site.admin_view(self.canjear_creditos_view),
                name="canjear-creditos",
            ), path(
                    'cargar-creditos-wallet/<int:wallet_id>/',
                    self.admin_site.admin_view(self.cargar_creditos_wallet_view),
                    name="cargar-creditos-wallet",
),
        ]
        return custom_urls + urls
    
   
    list_display = ('owner', 'balance_total', 'cargar_creditos', 'canjear_creditos')
    search_fields = ('user__username', 'empresa__nombre')
    list_filter = (WalletTypeFilter,)

    

def ajuste_manual_global(request):
    from django.shortcuts import render, redirect
    from django.contrib import messages
    from .models import Wallet, CreditTransaction

    if request.method == "POST":
        wallet_id = request.POST.get("wallet_id")
        amount = int(request.POST.get("amount"))
        tipo = request.POST.get("tipo")
        motivo = request.POST.get("motivo")

        wallet = Wallet.objects.get(id=wallet_id)

        if tipo == "empresa":
            wallet.balance_empresa += amount
        else:
            wallet.balance_personal += amount

        wallet.save()

        CreditTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type="adjustment",
            motivo=motivo,
            created_by=request.user
        )

        messages.success(request, "Ajuste realizado correctamente")
        return redirect("/admin/")

    wallets = Wallet.objects.all()

    return render(request, "admin/ajuste_manual.html", {"wallets": wallets})

from django.utils.html import format_html



from django.urls import path
from django.contrib import admin


admin_site = CustomAdminSite(name='custom_admin')

admin_site.register(Empresa, EmpresaAdmin)


admin_site.register(User, UserAdmin)

admin_site.register(UserProfile, UserProfileAdmin)
admin_site.register(Wallet, WalletAdmin)
admin_site.register(CreditTransaction, CreditTransactionAdmin)
admin_site.register(Equipo)
admin_site.register(Curso)