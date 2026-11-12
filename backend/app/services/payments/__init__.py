from app.core.config import settings
from app.services.payments.base import PaymentProvider


def get_payment_provider() -> PaymentProvider:
    if settings.PAYMENT_PROVIDER == "placeholder":
        from app.services.payments.placeholder import PlaceholderPaymentProvider

        return PlaceholderPaymentProvider()
    if settings.PAYMENT_PROVIDER == "paypal":
        from app.services.payments.paypal import PayPalProvider

        return PayPalProvider()
    raise RuntimeError(f"Unknown PAYMENT_PROVIDER '{settings.PAYMENT_PROVIDER}'")
