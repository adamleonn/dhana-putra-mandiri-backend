from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from inventory.models import Product, GoodsReceipt, StockMovement
from finance.services.journal_service import create_journal_entry, get_open_period
from core.services.audit import log_audit


@transaction.atomic
def confirm_goods_receipt(receipt: GoodsReceipt, confirmed_by) -> GoodsReceipt:
    """
    Konfirmasi Penerimaan Barang Masuk (BPB):
    1. Validasi status dan periode akuntansi aktif.
    2. Alokasikan biaya transportasi secara proporsional ke HPP produk.
    3. Biaya bongkar muat (kuli bongkar) TIDAK BOLEH masuk HPP, dicatat langsung sebagai beban operasional.
    4. Update stok fisik, stock_value, dan Moving Average HPP (select_for_update ordered by id).
    5. Terbitkan mutasi kartu stok (StockMovement IN).
    6. Terbitkan jurnal otomatis berpasangan: Dr Persediaan, Dr Beban Bongkar / Cr Hutang Dagang, Cr Kas/Hutang Biaya.
    """
    if receipt.status in ['confirmed', 'cancelled']:
        raise ValidationError(f"Goods Receipt '{receipt.receipt_number}' sudah berstatus '{receipt.status}'. Tidak dapat dikonfirmasi ulang.")

    period = get_open_period(receipt.receipt_date)
    receipt.accounting_period = period

    items = list(receipt.items.select_related('product').all())
    if not items:
        raise ValidationError("Goods Receipt tidak memiliki item barang.")

    total_purchase_value = Decimal('0.00')
    total_actual_qty = Decimal('0.00')

    for item in items:
        line_val = (item.qty_actual * item.purchase_price).quantize(Decimal('0.01'), ROUND_HALF_UP)
        item.line_total = line_val
        total_purchase_value += line_val
        total_actual_qty += item.qty_actual

    total_allocated_transport = Decimal('0.00')
    for idx, item in enumerate(items):
        if total_purchase_value > Decimal('0.00'):
            line_val = item.qty_actual * item.purchase_price
            if idx == len(items) - 1:
                allocated_transport = receipt.transport_cost - total_allocated_transport
            else:
                allocated_transport = ((line_val / total_purchase_value) * receipt.transport_cost).quantize(Decimal('0.01'), ROUND_HALF_UP)
        elif total_actual_qty > Decimal('0.00'):
            if idx == len(items) - 1:
                allocated_transport = receipt.transport_cost - total_allocated_transport
            else:
                allocated_transport = ((item.qty_actual / total_actual_qty) * receipt.transport_cost).quantize(Decimal('0.01'), ROUND_HALF_UP)
        else:
            allocated_transport = Decimal('0.00')

        total_allocated_transport += allocated_transport
        item.allocated_transport_cost = allocated_transport

        if item.qty_actual > Decimal('0.00'):
            item.effective_unit_cost = (
                ((item.qty_actual * item.purchase_price) + allocated_transport) / item.qty_actual
            ).quantize(Decimal('0.01'), ROUND_HALF_UP)
        else:
            item.effective_unit_cost = item.purchase_price

        item.save(update_fields=['line_total', 'allocated_transport_cost', 'effective_unit_cost'])

    receipt.payable_amount = total_purchase_value + receipt.transport_cost
    receipt.save(update_fields=['payable_amount', 'accounting_period'])

    product_ids = sorted([item.product_id for item in items])
    locked_products = {
        p.id: p
        for p in Product.objects.filter(id__in=product_ids).select_for_update()
    }

    for item in items:
        product = locked_products[item.product_id]
        if item.qty_actual > Decimal('0.00'):
            old_stock = product.current_stock
            old_stock_value = product.stock_value

            incoming_qty = item.qty_actual
            incoming_value = (incoming_qty * item.purchase_price) + item.allocated_transport_cost

            new_stock = old_stock + incoming_qty
            new_stock_value = old_stock_value + incoming_value

            product.current_stock = new_stock
            product.stock_value = new_stock_value
            product.moving_average_hpp = (new_stock_value / new_stock).quantize(Decimal('0.01'), ROUND_HALF_UP)
            product.save(update_fields=['current_stock', 'stock_value', 'moving_average_hpp', 'updated_at'])

            StockMovement.objects.create(
                product=product,
                movement_date=timezone.now(),
                movement_type='IN',
                qty=incoming_qty,
                unit_cost=item.effective_unit_cost,
                total_cost=incoming_value,
                stock_before=old_stock,
                stock_after=new_stock,
                hpp_after=product.moving_average_hpp,
                goods_receipt_item=item,
                reference_type='GOODS_RECEIPT',
                reference_id=str(receipt.id),
                created_by=confirmed_by,
                notes=f"Penerimaan BPB {receipt.receipt_number}"
            )

    journal_lines = [
        {
            'account_code': '1140',
            'debit': receipt.payable_amount,
            'credit': Decimal('0.00'),
            'memo': f"Persediaan Barang Masuk BPB {receipt.receipt_number}"
        },
        {
            'account_code': '2110',
            'debit': Decimal('0.00'),
            'credit': receipt.payable_amount,
            'memo': f"Hutang Dagang BPB {receipt.receipt_number} ({receipt.supplier.name})"
        }
    ]

    if receipt.unloading_cost > Decimal('0.00'):
        journal_lines.append({
            'account_code': '6120',
            'debit': receipt.unloading_cost,
            'credit': Decimal('0.00'),
            'memo': f"Beban Kuli Bongkar BPB {receipt.receipt_number}"
        })
        journal_lines.append({
            'account_code': '1110',
            'debit': Decimal('0.00'),
            'credit': receipt.unloading_cost,
            'memo': f"Kas Keluar Ongkos Kuli Bongkar BPB {receipt.receipt_number}"
        })

    create_journal_entry(
        transaction_date=receipt.receipt_date,
        reference_type='GOODS_RECEIPT',
        reference_id=str(receipt.id),
        description=f"Penerimaan Barang BPB {receipt.receipt_number} dari {receipt.supplier.name}",
        lines=journal_lines,
        posted_by=confirmed_by
    )

    receipt.status = 'confirmed'
    receipt.confirmed_by = confirmed_by
    receipt.confirmed_at = timezone.now()
    receipt.save(update_fields=['status', 'confirmed_by', 'confirmed_at', 'updated_at'])

    log_audit(
        actor=confirmed_by,
        action='CONFIRM',
        instance=receipt,
        changes={
            'status': 'confirmed',
            'payable_amount': str(receipt.payable_amount),
            'items_count': len(items)
        }
    )

    return receipt
