from decimal import Decimal


class InsufficientStockError(Exception):
    """Raised when physical warehouse stock is insufficient during delivery confirmation (HTTP 409)."""
    def __init__(self, product_sku: str, product_name: str, requested_qty: Decimal, available_stock: Decimal):
        self.product_sku = product_sku
        self.product_name = product_name
        self.requested_qty = requested_qty
        self.available_stock = available_stock
        message = (
            f"Stok tidak mencukupi untuk '{product_name}' (SKU: {product_sku}). "
            f"Permintaan: {requested_qty}, Stok Tersedia: {available_stock}."
        )
        super().__init__(message)

