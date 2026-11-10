from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from inventory.models import Product, GoodsReceipt, StockMovement
from finance.services import create_journal_entry
from config.sequence_generator import generate_document_number


@transaction.atomic
def confirm_goods_receipt(receipt: GoodsReceipt, confirmed_by) -> GoodsReceipt:
    if receipt.status in ['confirmed', 'cancelled']:
        raise ValidationError(f"Goods Receipt already has status '{receipt.status}'. Cannot re-confirm.")

    items = list(receipt.items.select_related('product').all())
    if not items:
        raise ValidationError("Cannot confirm Goods Receipt with no items.")

    total_purchase_value = Decimal('0.00')
    total_actual_qty = Decimal('0.00')
    has_discrepancy = False

    for item in items:
        if item.qty_actual < item.qty_ordered:
            has_discrepancy = True
        line_val = item.qty_actual * item.purchase_price
        total_purchase_value += line_val
        total_actual_qty += item.qty_actual

    total_allocated_transport = Decimal('0.00')
    for idx, item in enumerate(items):
        if total_purchase_value > Decimal('0.00'):
            line_val = item.qty_actual * item.purchase_price
            if idx == len(items) - 1:
                allocated_transport = receipt.transport_cost - total_allocated_transport
            else:
                allocated_transport = (line_val / total_purchase_value) * receipt.transport_cost
        elif total_actual_qty > Decimal('0.00'):
            if idx == len(items) - 1:
                allocated_transport = receipt.transport_cost - total_allocated_transport
            else:
                allocated_transport = (item.qty_actual / total_actual_qty) * receipt.transport_cost
        else:
            allocated_transport = Decimal('0.00')

        allocated_transport = allocated_transport.quantize(Decimal('0.01'))
        total_allocated_transport += allocated_transport

        item.allocated_transport_cost = allocated_transport
        if item.qty_actual > Decimal('0.00'):
            item.effective_unit_cost = (
                (item.qty_actual * item.purchase_price) + allocated_transport
            ) / item.qty_actual
        else:
            item.effective_unit_cost = item.purchase_price

        item.save(update_fields=['allocated_transport_cost', 'effective_unit_cost'])

    total_inventory_asset_increase = Decimal('0.00')

    product_ids = [item.product_id for item in items]
    locked_products = {
        p.id: p
        for p in Product.objects.filter(id__in=product_ids).select_for_update()
    }

    for item in items:
        product = locked_products[item.product_id]
        if item.qty_actual > Decimal('0.00'):
            old_stock = product.current_stock
            old_hpp = product.moving_average_hpp

            incoming_qty = item.qty_actual
            incoming_effective_cost = item.effective_unit_cost

            new_stock = old_stock + incoming_qty
            if new_stock > Decimal('0.00'):
                new_hpp = (
                    (old_stock * old_hpp) + (incoming_qty * incoming_effective_cost)
                ) / new_stock
            else:
                new_hpp = incoming_effective_cost

            product.current_stock = new_stock
            product.moving_average_hpp = new_hpp.quantize(Decimal('0.01'))
            product.save(update_fields=['current_stock', 'moving_average_hpp'])

            StockMovement.objects.create(
                product=product,
                movement_date=timezone.now(),
                movement_type='IN',
                reference_type='GOODS_RECEIPT',
                reference_number=receipt.receipt_number,
                qty=incoming_qty,
                unit_cost=incoming_effective_cost,
                stock_before=old_stock,
                stock_after=new_stock,
                created_by=confirmed_by,
                notes=f"Penerimaan Barang Ref {receipt.receipt_number}"
            )

            total_inventory_asset_increase += (incoming_qty * incoming_effective_cost)

    supplier_display_name = receipt.supplier.name if receipt.supplier else receipt.supplier_name

    journal_lines = [
        {
            'account_code': '1140',
            'debit': total_inventory_asset_increase.quantize(Decimal('0.01')),
            'credit': Decimal('0.00'),
            'memo': f"Persediaan Masuk GR {receipt.receipt_number} ({supplier_display_name})"
        }
    ]

    total_supplier_payable = total_inventory_asset_increase.quantize(Decimal('0.01'))
    journal_lines.append({
        'account_code': '2110',
        'debit': Decimal('0.00'),
        'credit': total_supplier_payable,
        'memo': f"Hutang Dagang Supplier {supplier_display_name}"
    })

    if receipt.unloading_cost > Decimal('0.00'):
        journal_lines.append({
            'account_code': '6100',
            'debit': receipt.unloading_cost,
            'credit': Decimal('0.00'),
            'memo': f"Biaya Kuli Bongkar GR {receipt.receipt_number}"
        })
        journal_lines.append({
            'account_code': '2130',
            'debit': Decimal('0.00'),
            'credit': receipt.unloading_cost,
            'memo': f"Hutang Ongkos Bongkar Muat GR {receipt.receipt_number}"
        })

    jv_number = generate_document_number('JV', receipt.receipt_date)

    create_journal_entry(
        entry_number=jv_number,
        transaction_date=receipt.receipt_date,
        reference_type='GOODS_RECEIPT',
        reference_id=receipt.receipt_number,
        description=f"Penerimaan Barang Supplier {supplier_display_name} Ref {receipt.receipt_number}",
        lines=journal_lines,
        posted_by=confirmed_by
    )

    receipt.status = 'discrepancy_detected' if has_discrepancy else 'confirmed'
    receipt.confirmed_at = timezone.now()
    receipt.received_by = confirmed_by
    receipt.save(update_fields=['status', 'confirmed_at', 'received_by'])

    return receipt
