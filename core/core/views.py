from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from accounts.models import Empresa, Wallet, CreditTransaction, Equipo

@csrf_exempt
def zoho_webhook(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            empresa_nombre = data.get("empresa")
            equipo_nombre = data.get("equipo")

            empresa = Empresa.objects.get(nombre=empresa_nombre)
            equipo = Equipo.objects.get(nombre=equipo_nombre)

            wallet = Wallet.objects.get(empresa=empresa)

            wallet.balance += equipo.creditos
            wallet.save()

            CreditTransaction.objects.create(
                wallet=wallet,
                amount=equipo.creditos,
                transaction_type="purchase"
            )

            return JsonResponse({"status": "ok"})

        except Empresa.DoesNotExist:
            return JsonResponse({"error": "empresa no encontrada"}, status=404)

        except Equipo.DoesNotExist:
            return JsonResponse({"error": "equipo no encontrado"}, status=404)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)