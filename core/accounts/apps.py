from django.apps import AppConfig

class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        print("ACCOUNTS READY")  # 👈 debug
        import accounts.signals