from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from inventory.models import Product, Delivery, StockMovement
from .exceptions import InsufficientStockError
from finance.services import create_journal_entry
from config.sequence_generator import generate_document_number


@transaction.atomic
def confirm_delivery_atomic(delivery: Delivery, confirmed_by, auto_generate_invoice: bool = True) -> Delivery:
    if delivery.status == 'confirmed':
        raise ValidationError(f"Delivery '{delivery.delivery_number}' has already been confirmed.")
    if delivery.status == 'cancelled':
        raise ValidationError(f"Cannot confirm cancelled delivery '{delivery.delivery_number}'.")

    items = list(delivery.items.select_related('product').all())
    if not items:
        raise ValidationError("Cannot confirm delivery with no items.")

    product_ids = [item.product_id for item in items]
    locked_products = {
        p.id: p
        for p in Product.objects.filter(id__in=product_ids).select_for_update()
    }

    for item in items:
        effective_qty = item.effective_qty
        product = locked_products[item.product_id]
        if product.current_stock < effective_qty:
            raise InsufficientStockError(
                product_sku=product.sku,
                product_name=product.name,
                requested_qty=effective_qty,
                available_stock=product.current_stock
            )

    total_cogs = Decimal('0.00')
    total_revenue = Decimal('0.00')

    for item in items:
        effective_qty = item.effective_qty
        product = locked_products[item.product_id]
        old_stock = product.current_stock
        new_stock = old_stock - effective_qty
        product.current_stock = new_stock
        product.save(update_fields=['current_stock'])

        item.hpp_at_delivery = product.moving_average_hpp
        if item.qty_delivered == Decimal('0.00'):
            item.qty_delivered = item.qty
        item.save(update_fields=['hpp_at_delivery', 'qty_delivered'])

        StockMovement.objects.create(
            product=product,
            movement_date=timezone.now(),
            movement_type='OUT',
            reference_type='DELIVERY',
            reference_number=delivery.delivery_number,
            qty=effective_qty,
            unit_cost=product.moving_average_hpp,
            stock_before=old_stock,
            stock_after=new_stock,
            created_by=confirmed_by,
            notes=f"Pengiriman Surat Jalan Ref {delivery.delivery_number}"
        )

        line_cogs = (effective_qty * item.hpp_at_delivery).quantize(Decimal('0.01'))
        line_revenue = (effective_qty * product.selling_price).quantize(Decimal('0.01'))

        total_cogs += line_cogs
        total_revenue += line_revenue

    customer_display_name = delivery.customer.name if delivery.customer else delivery.customer_name

    journal_lines = [
        {
            'account_code': '1130',
            'debit': total_revenue,
            'credit': Decimal('0.00'),
            'memo': f"Piutang Pengiriman {delivery.delivery_number} ({customer_display_name})"
        },
        {
            'account_code': '4100',
            'debit': Decimal('0.00'),
            'credit': total_revenue,
            'memo': f"Penjualan Surat Jalan {delivery.delivery_number}"
        },
        {
            'account_code': '5100',
            'debit': total_cogs,
            'credit': Decimal('0.00'),
            'memo': f"HPP Pengiriman {delivery.delivery_number}"
        },
        {
            'account_code': '1140',
            'debit': Decimal('0.00'),
            'credit': total_cogs,
            'memo': f"Pengurangan Stok Fisik {delivery.delivery_number}"
        }
    ]

    jv_number = generate_document_number('JV', delivery.delivery_date)

    create_journal_entry(
        entry_number=jv_number,
        transaction_date=delivery.delivery_date,
        reference_type='SALES_DELIVERY',
        reference_id=delivery.delivery_number,
        description=f"Konfirmasi Pengiriman Surat Jalan {delivery.delivery_number} ke {customer_display_name}",
        lines=journal_lines,
        posted_by=confirmed_by
    )

    delivery.status = 'confirmed'
    delivery.confirmed_at = timezone.now()
    delivery.confirmed_by = confirmed_by
    delivery.save(update_fields=['status', 'confirmed_at', 'confirmed_by'])

    if auto_generate_invoice:
        from finance.models import SalesInvoice, SalesInvoiceItem
        inv_number = generate_document_number('INV', delivery.delivery_date)
        invoice, _ = SalesInvoice.objects.update_or_create(
            delivery=delivery,
            defaults={
                'invoice_number': inv_number,
                'customer': delivery.customer,
                'customer_name': customer_display_name,
                'invoice_date': delivery.delivery_date,
                'due_date': delivery.delivery_date.replace(day=min(delivery.delivery_date.day + 14, 28)),
                'subtotal': total_revenue,
                'total_amount': total_revenue,
                'status': 'unpaid',
                'created_by': confirmed_by,
                'notes': f"Faktur otomatis Surat Jalan {delivery.delivery_number}"
            }
        )
        invoice.items.all().delete()
        for item in items:
            SalesInvoiceItem.objects.create(
                invoice=invoice,
                product=item.product,
                qty_ordered=item.qty,
                qty_delivered=item.effective_qty,
                qty=item.effective_qty,
                unit_price=item.product.selling_price,
                line_total=item.effective_qty * item.product.selling_price
            )

    return delivery
