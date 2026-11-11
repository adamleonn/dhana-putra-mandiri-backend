from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from inventory.models import Product, Delivery, StockMovement
from config.exceptions import InsufficientStockError
from finance.services.journal_service import create_journal_entry, get_open_period
from core.services.audit import log_audit


@transaction.atomic
def confirm_delivery_atomic(delivery: Delivery, confirmed_by) -> Delivery:
    """
    Konfirmasi Pengiriman Fisik Surat Jalan (INVOICE-FIRST):
    1. Validasi status: tidak boleh dobel konfirmasi atau kirim draf yang dibatalkan.
    2. Validasi konsistensi pelanggan: delivery.customer == delivery.sales_invoice.customer.
    3. Validasi periode akuntansi aktif.
    4. Kunci baris Product dengan select_for_update() urut berdasarkan ID (deadlock prevention).
    5. Cek ketersediaan stok fisik vs qty_delivered (jika kurang -> InsufficientStockError -> HTTP 409).
    6. Potong stok, update stock_value produk, snapshot HPP, mutasi kartu stok (StockMovement OUT).
    7. Baris dengan qty_delivered == 0 dihitung 0 HPP dan tidak memotong stok (mengatasi bug qty 0).
    8. Hitung ulang total SalesInvoice berdasarkan kuantitas fisik yang benar-benar terkirim.
    9. Terbitkan jurnal otomatis berpasangan: Dr Piutang / Cr Penjualan dan Dr HPP / Cr Persediaan.
    """
    if delivery.status == 'confirmed':
        raise ValidationError(f"Delivery '{delivery.delivery_number}' sudah dikonfirmasi sebelumnya.")
    if delivery.status == 'cancelled':
        raise ValidationError(f"Delivery '{delivery.delivery_number}' telah dibatalkan.")

    sales_invoice = delivery.sales_invoice
    if not sales_invoice:
        raise ValidationError("Alur Invoice-First mewajibkan Surat Jalan terhubung dengan Sales Invoice.")

    if delivery.customer_id != sales_invoice.customer_id:
        raise ValidationError(
            f"Inkonsistensi data: Pelanggan Surat Jalan ({delivery.customer.name}) "
            f"tidak cocok dengan Pelanggan Faktur Penjualan ({sales_invoice.customer.name})."
        )

    get_open_period(delivery.delivery_date)

    items = list(delivery.items.select_related('product', 'sales_invoice_item').all())
    if not items:
        raise ValidationError("Surat Jalan tidak memiliki daftar item barang.")

    product_ids = sorted([item.product_id for item in items])
    locked_products = {
        p.id: p
        for p in Product.objects.filter(id__in=product_ids).select_for_update()
    }

    # Step 1: Validasi stok untuk seluruh baris yang dikonfirmasi
    for item in items:
        deliver_qty = item.effective_qty
        if deliver_qty > Decimal('0.00'):
            product = locked_products[item.product_id]
            if product.current_stock < deliver_qty:
                raise InsufficientStockError(
                    message=(
                        f"Stok gudang tidak mencukupi untuk SKU '{product.sku}' ({product.name}). "
                        f"Diminta: {deliver_qty} {product.uom}, Tersedia: {product.current_stock} {product.uom}."
                    ),
                    product_sku=product.sku,
                    product_name=product.name,
                    requested_qty=deliver_qty,
                    available_stock=product.current_stock
                )

    total_cogs = Decimal('0.00')

    # Step 2: Eksekusi pemotongan stok dan snapshot
    for item in items:
        deliver_qty = item.effective_qty
        product = locked_products[item.product_id]

        if deliver_qty > Decimal('0.00'):
            old_stock = product.current_stock
            new_stock = old_stock - deliver_qty
            product.current_stock = new_stock

            item.hpp_at_delivery = product.moving_average_hpp
            item.qty_delivered = deliver_qty
            item.total_cogs = (deliver_qty * item.hpp_at_delivery).quantize(Decimal('0.01'), ROUND_HALF_UP)
            item.save(update_fields=['hpp_at_delivery', 'qty_delivered', 'total_cogs'])

            product.stock_value = max(Decimal('0.00'), product.stock_value - item.total_cogs)
            product.save(update_fields=['current_stock', 'stock_value', 'updated_at'])

            StockMovement.objects.create(
                product=product,
                movement_date=timezone.now(),
                movement_type='OUT',
                qty=deliver_qty,
                unit_cost=item.hpp_at_delivery,
                total_cost=item.total_cogs,
                stock_before=old_stock,
                stock_after=new_stock,
                hpp_after=product.moving_average_hpp,
                delivery_item=item,
                reference_type='DELIVERY',
                reference_id=str(delivery.id),
                created_by=confirmed_by,
                notes=f"Pengiriman Surat Jalan {delivery.delivery_number} ke {delivery.customer.name}"
            )

            total_cogs += item.total_cogs

            if item.sales_invoice_item:
                inv_item = item.sales_invoice_item
                inv_item.qty_delivered = deliver_qty
                inv_item.line_total = max(
                    Decimal('0.00'),
                    (deliver_qty * inv_item.unit_price) - inv_item.discount_amount
                ).quantize(Decimal('0.01'), ROUND_HALF_UP)
                inv_item.save(update_fields=['qty_delivered', 'line_total'])
        else:
            # Baris 0 delivered (tidak terkirim / batal)
            item.qty_delivered = Decimal('0.00')
            item.hpp_at_delivery = Decimal('0.00')
            item.total_cogs = Decimal('0.00')
            item.save(update_fields=['qty_delivered', 'hpp_at_delivery', 'total_cogs'])

            if item.sales_invoice_item:
                inv_item = item.sales_invoice_item
                inv_item.qty_delivered = Decimal('0.00')
                inv_item.line_total = Decimal('0.00')
                inv_item.save(update_fields=['qty_delivered', 'line_total'])

    # Step 3: Hitung ulang total SalesInvoice berdasarkan yang benar-benar terkirim
    new_subtotal = Decimal('0.00')
    for inv_line in sales_invoice.items.all():
        new_subtotal += inv_line.line_total

    sales_invoice.subtotal = new_subtotal
    sales_invoice.total_amount = max(Decimal('0.00'), new_subtotal - sales_invoice.discount_amount)
    sales_invoice.status = 'approved'

    # Step 4: Terbitkan Jurnal Akuntansi Double-Entry
    journal_lines = []
    if sales_invoice.total_amount > Decimal('0.00'):
        journal_lines.extend([
            {
                'account_code': '1130',
                'debit': sales_invoice.total_amount,
                'credit': Decimal('0.00'),
                'memo': f"Piutang Dagang Faktur {sales_invoice.invoice_number} ({delivery.customer.name})"
            },
            {
                'account_code': '4100',
                'debit': Decimal('0.00'),
                'credit': sales_invoice.total_amount,
                'memo': f"Pendapatan Penjualan Faktur {sales_invoice.invoice_number}"
            }
        ])

    if total_cogs > Decimal('0.00'):
        journal_lines.extend([
            {
                'account_code': '5100',
                'debit': total_cogs,
                'credit': Decimal('0.00'),
                'memo': f"Beban Pokok Penjualan (HPP) SJ {delivery.delivery_number}"
            },
            {
                'account_code': '1140',
                'debit': Decimal('0.00'),
                'credit': total_cogs,
                'memo': f"Pengurangan Persediaan Barang Dagang SJ {delivery.delivery_number}"
            }
        ])

    if journal_lines:
        journal_entry = create_journal_entry(
            transaction_date=delivery.delivery_date,
            reference_type='DELIVERY',
            reference_id=str(delivery.id),
            description=f"Faktur & Pengiriman SJ {delivery.delivery_number} ke {delivery.customer.name}",
            lines=journal_lines,
            posted_by=confirmed_by
        )
        sales_invoice.journal_entry = journal_entry
    sales_invoice.save(update_fields=['subtotal', 'total_amount', 'status', 'journal_entry', 'updated_at'])

    delivery.status = 'confirmed'
    delivery.confirmed_by = confirmed_by
    delivery.confirmed_at = timezone.now()
    delivery.save(update_fields=['status', 'confirmed_by', 'confirmed_at', 'updated_at'])

    log_audit(
        actor=confirmed_by,
        action='CONFIRM',
        instance=delivery,
        changes={
            'status': 'confirmed',
            'invoice_number': sales_invoice.invoice_number,
            'invoice_total': str(sales_invoice.total_amount),
            'total_cogs': str(total_cogs)
        }
    )

    return delivery
