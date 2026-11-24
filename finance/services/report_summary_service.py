"""
Asisten ringkasan laporan berbasis Small Language Model (SLM).

Alur:
1. Data laporan dihitung ulang di server dengan generator yang sama seperti
   endpoint laporan (bukan data kiriman browser).
2. Dari data itu diekstrak *fakta* ringkas yang relevan (angka sudah
   diformat Rupiah) dan dikelompokkan: ringkasan, tren, pencapaian, masalah,
   tindak lanjut. Bila fakta tidak memadai, ringkasan tidak dibuat.
3. Fakta dikirim ke SLM lewat API kompatibel OpenAI (`/chat/completions`) —
   default Ollama lokal — dengan instruksi hanya merangkai ulang fakta.
4. Keluaran diverifikasi: nominal Rupiah yang tidak ada di fakta ditolak.

Konfigurasi dibaca dari settings (sumber: environment / .env), lihat
`AI_SUMMARY_*` di config/settings.py.
"""

import json
import logging
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Dict, List

from django.conf import settings
from django.utils import timezone

from finance.reports import (
    generate_annual_report,
    generate_balance_sheet,
    generate_pie_chart_analytics,
    generate_product_sales_report,
    generate_sales_trends,
)
from finance.reports.sales_reports import sales_by_brand_and_size

logger = logging.getLogger(__name__)

INSUFFICIENT_MARKER = 'DATA_TIDAK_CUKUP'
INSUFFICIENT_MESSAGE = (
    'Ringkasan belum dapat dibuat karena data pada laporan ini belum cukup '
    '(misalnya belum ada transaksi pada periode yang dipilih).'
)

CATEGORIES = (
    ('ringkasan', 'RINGKASAN'),
    ('tren', 'TREN'),
    ('pencapaian', 'PENCAPAIAN'),
    ('masalah', 'MASALAH'),
    ('tindak_lanjut', 'TINDAK LANJUT'),
)


class SummaryError(Exception):
    """Kesalahan yang aman ditampilkan ke pengguna."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class ReportFacts:
    title: str
    period: str
    facts: Dict[str, List[str]] = field(default_factory=lambda: {key: [] for key, _ in CATEGORIES})

    def add(self, category: str, text: str) -> None:
        self.facts[category].append(text)

    @property
    def is_empty(self) -> bool:
        return not any(self.facts.values())

    def as_list(self) -> List[Dict[str, str]]:
        return [{'category': key, 'text': text} for key, _ in CATEGORIES for text in self.facts[key]]


# --------------------------------------------------------------------------
# Format angka (gaya Indonesia)
# --------------------------------------------------------------------------

def _d(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value or 0))


def rupiah(value: Any) -> str:
    amount = _d(value).quantize(Decimal('1'))
    text = f'{abs(amount):,.0f}'.replace(',', '.')
    return f'-Rp {text}' if amount < 0 else f'Rp {text}'


def persen(value: Any) -> str:
    return f'{float(value):.1f}%'.replace('.', ',')


def _share(part: Decimal, total: Decimal) -> float:
    return float(part / total * 100) if total > 0 else 0.0


# --------------------------------------------------------------------------
# Ekstraksi fakta per jenis laporan (hanya data relevan, tanpa interpretasi
# yang tidak didukung angka).
# --------------------------------------------------------------------------

def _monthly_facts(out: ReportFacts, trends: List[Dict[str, Any]]) -> None:
    active = [t for t in trends if _d(t['total_sales']) > 0]
    if not active:
        return
    out.add('tren', f'Penjualan tercatat pada {len(active)} dari 12 bulan.')
    best = max(active, key=lambda t: _d(t['total_sales']))
    out.add('pencapaian', f"Bulan dengan penjualan tertinggi: {best['month_name']} ({rupiah(best['total_sales'])}).")
    if len(active) > 1:
        worst = min(active, key=lambda t: _d(t['total_sales']))
        out.add('tren', f"Bulan dengan penjualan terendah (di antara bulan aktif): {worst['month_name']} ({rupiah(worst['total_sales'])}).")
        last, prev = active[-1], active[-2]
        diff = _d(last['total_sales']) - _d(prev['total_sales'])
        if _d(prev['total_sales']) > 0:
            change = _share(abs(diff), _d(prev['total_sales']))
            direction = 'naik' if diff > 0 else 'turun' if diff < 0 else 'stabil'
            out.add('tren', (
                f"Penjualan {last['month_name']} {direction} {persen(change)} dibanding "
                f"{prev['month_name']} ({rupiah(prev['total_sales'])} menjadi {rupiah(last['total_sales'])})."
            ))
    losses = [t['month_name'] for t in active if _d(t['gross_profit']) < 0]
    if losses:
        out.add('masalah', f"Laba kotor negatif pada bulan: {', '.join(losses)}.")
        out.add('tindak_lanjut', 'Tinjau harga jual dan HPP pada bulan dengan laba kotor negatif.')


def _facts_sales_trends(params: Dict[str, Any]) -> ReportFacts:
    year = params['year']
    trends = generate_sales_trends(year)
    out = ReportFacts(title='Tren Penjualan 12 Bulan', period=f'Tahun {year}')
    total_sales = sum((_d(t['total_sales']) for t in trends), Decimal('0'))
    if total_sales <= 0:
        return out
    total_profit = sum((_d(t['gross_profit']) for t in trends), Decimal('0'))
    out.add('ringkasan', f'Total penjualan tahun {year}: {rupiah(total_sales)}.')
    out.add('ringkasan', f'Total laba kotor: {rupiah(total_profit)} (margin kotor {persen(_share(total_profit, total_sales))}).')
    _monthly_facts(out, trends)

    mix = sales_by_brand_and_size(year)
    if mix:
        by_brand: Dict[str, Decimal] = {}
        for row in mix:
            brand = row['brand'] or 'Lainnya'
            by_brand[brand] = by_brand.get(brand, Decimal('0')) + _d(row['revenue'])
        brand, value = max(by_brand.items(), key=lambda kv: kv[1])
        out.add('pencapaian', f'Merek dengan kontribusi penjualan terbesar: {brand} ({rupiah(value)}, {persen(_share(value, total_sales))} dari total).')
    return out


def _facts_product_sales(params: Dict[str, Any]) -> ReportFacts:
    year = params['year']
    report = generate_product_sales_report(year)
    out = ReportFacts(title='Penjualan & Margin Produk', period=f'Tahun {year}')
    products = report['products']
    revenue = _d(report['total_revenue'])
    if not products or revenue <= 0:
        return out
    gross = _d(report['total_gross_profit'])
    out.add('ringkasan', f'{len(products)} produk terjual dengan total pendapatan {rupiah(revenue)}.')
    out.add('ringkasan', f'Total laba kotor: {rupiah(gross)} (margin kotor {persen(_share(gross, revenue))}).')

    top = products[:3]
    top_text = '; '.join(f"{p['name']} ({rupiah(p['revenue'])})" for p in top)
    out.add('pencapaian', f'Produk dengan pendapatan tertinggi: {top_text}.')
    best_margin = max(products, key=lambda p: p['margin_percentage'])
    out.add('pencapaian', f"Margin tertinggi: {best_margin['name']} ({persen(best_margin['margin_percentage'])}).")

    if len(products) > 1:
        top_share = _share(_d(products[0]['revenue']), revenue)
        out.add('tren', f"Produk teratas ({products[0]['name']}) menyumbang {persen(top_share)} dari total pendapatan.")

    negative = [p['name'] for p in products if _d(p['gross_profit']) < 0]
    if negative:
        out.add('masalah', f"Produk dengan laba kotor negatif: {', '.join(negative)}.")
        out.add('tindak_lanjut', 'Evaluasi harga jual produk dengan laba kotor negatif terhadap HPP rata-ratanya.')
    out_of_stock = [p['name'] for p in products if _d(p['current_stock']) <= 0]
    if out_of_stock:
        out.add('masalah', f"Produk laku yang stoknya kini habis: {', '.join(out_of_stock)}.")
        out.add('tindak_lanjut', 'Pertimbangkan pengadaan ulang untuk produk laku yang stoknya habis.')
    return out


def _facts_annual(params: Dict[str, Any]) -> ReportFacts:
    year = params['year']
    report = generate_annual_report(year)
    s = report['summary']
    out = ReportFacts(title='Ringkasan Keuangan Tahunan', period=f'Tahun {year}')
    revenue = _d(s['total_revenue'])
    if revenue <= 0:
        return out
    opex = s['operating_expenses']
    net = _d(s['net_operating_profit'])
    out.add('ringkasan', f"Pendapatan {rupiah(revenue)}, HPP {rupiah(s['total_cogs'])}, laba kotor {rupiah(s['gross_profit'])}.")
    out.add('ringkasan', f"Total beban operasional {rupiah(opex['total'])}; laba bersih operasional {rupiah(net)} (margin bersih {persen(s['net_profit_margin_pct'])}).")

    components = {
        'gaji & upah': opex['payroll_expense'],
        'kuli bongkar': opex['kuli_bongkar_expense'],
        'transportasi armada': opex['armada_transport_expense'],
        'kantor & umum': opex['office_general_expense'],
    }
    total_opex = _d(opex['total'])
    if total_opex > 0:
        name, value = max(components.items(), key=lambda kv: _d(kv[1]))
        out.add('tren', f'Komponen beban terbesar: {name} ({rupiah(value)}, {persen(_share(_d(value), total_opex))} dari total beban).')

    if net > 0:
        out.add('pencapaian', f'Perusahaan mencatat laba bersih operasional {rupiah(net)}.')
    elif net < 0:
        out.add('masalah', f'Perusahaan mencatat rugi operasional {rupiah(abs(net))}.')
        out.add('tindak_lanjut', 'Tinjau komponen beban operasional terbesar dan margin produk.')
    _monthly_facts(out, report['monthly_breakdown'])
    return out


def _facts_balance_sheet(params: Dict[str, Any]) -> ReportFacts:
    as_of = params['as_of_date']
    report = generate_balance_sheet(as_of)
    out = ReportFacts(title='Neraca (Balance Sheet)', period=f'Per tanggal {as_of.isoformat()}')
    assets = report['assets']
    total_assets = _d(assets['total_assets'])
    total_liab = _d(report['liabilities']['total_liabilities'])
    equity = report['equity']
    if total_assets == 0 and total_liab == 0 and _d(equity['total_equity']) == 0:
        return out

    out.add('ringkasan', (
        f"Total aktiva {rupiah(total_assets)}, total kewajiban {rupiah(total_liab)}, "
        f"total ekuitas {rupiah(equity['total_equity'])}."
    ))
    kas = _d(assets['kas_dan_bank']['subtotal'])
    piutang = _d(assets['piutang_usaha'])
    persediaan = _d(assets['persediaan_barang_dagang'])
    out.add('ringkasan', f'Kas & bank {rupiah(kas)}, piutang usaha {rupiah(piutang)}, persediaan {rupiah(persediaan)}.')
    if total_assets > 0:
        out.add('tren', (
            f'Komposisi aktiva: kas & bank {persen(_share(kas, total_assets))}, '
            f'piutang {persen(_share(piutang, total_assets))}, persediaan {persen(_share(persediaan, total_assets))}.'
        ))
        if _share(piutang, total_assets) >= 40:
            out.add('masalah', f'Piutang usaha mencapai {persen(_share(piutang, total_assets))} dari total aktiva.')
            out.add('tindak_lanjut', 'Perkuat penagihan piutang pelanggan.')

    laba = _d(equity['laba_periode_berjalan'])
    if laba > 0:
        out.add('pencapaian', f'Laba periode berjalan {rupiah(laba)}.')
    elif laba < 0:
        out.add('masalah', f'Rugi periode berjalan {rupiah(abs(laba))}.')
    if total_liab > 0 and kas < total_liab:
        out.add('masalah', f'Kas & bank ({rupiah(kas)}) lebih kecil dari total kewajiban ({rupiah(total_liab)}).')
        out.add('tindak_lanjut', 'Jadwalkan pembayaran kewajiban sesuai ketersediaan kas.')

    summary = report['summary']
    if summary['is_balanced']:
        out.add('pencapaian', 'Neraca seimbang (aktiva = kewajiban + ekuitas).')
    else:
        out.add('masalah', f"Neraca tidak seimbang, selisih {rupiah(summary['difference'])}.")
        out.add('tindak_lanjut', 'Periksa jurnal yang belum lengkap atau salah akun.')
    return out


def _facts_pie_charts(params: Dict[str, Any]) -> ReportFacts:
    report = generate_pie_chart_analytics()
    out = ReportFacts(title='Distribusi Persediaan', period=f'Posisi stok per {timezone.localdate().isoformat()}')
    total = _d(report['total_portfolio_value'])
    brands = report['brand_distribution']
    sizes = report['package_size_distribution']
    if total <= 0 or not brands:
        return out
    out.add('ringkasan', f'Total nilai persediaan {rupiah(total)} dari {len(brands)} merek.')
    top = brands[0]
    out.add('tren', f"Merek dengan nilai stok terbesar: {top['label']} ({rupiah(top['stock_value'])}, {persen(top['percentage'])}).")
    if sizes:
        out.add('tren', f"Ukuran kemasan dengan nilai stok terbesar: {sizes[0]['label']} ({persen(sizes[0]['percentage'])}).")
    if top['percentage'] >= 50:
        out.add('masalah', f"Persediaan terkonsentrasi pada satu merek ({top['label']}, {persen(top['percentage'])}).")
        out.add('tindak_lanjut', 'Pertimbangkan diversifikasi stok antar merek.')
    empty = [b['label'] for b in brands if _d(b['stock_qty']) <= 0]
    if empty:
        out.add('masalah', f"Merek tanpa stok tersisa: {', '.join(empty)}.")
    return out


REPORT_BUILDERS: Dict[str, Callable[[Dict[str, Any]], ReportFacts]] = {
    'sales-trends': _facts_sales_trends,
    'product-sales': _facts_product_sales,
    'annual': _facts_annual,
    'balance-sheet': _facts_balance_sheet,
    'pie-charts': _facts_pie_charts,
}


# --------------------------------------------------------------------------
# Pemanggilan SLM
# --------------------------------------------------------------------------

SYSTEM_PROMPT = (
    'Anda asisten yang merangkum laporan bisnis untuk manajemen dalam bahasa Indonesia '
    'yang jelas, singkat, dan mudah dipahami.\n'
    'Aturan wajib:\n'
    '1. Gunakan HANYA fakta yang diberikan. Jangan menambah angka, nama, sebab, atau '
    'kesimpulan yang tidak tertulis di fakta.\n'
    '2. Salin angka persis seperti tertulis (format Rupiah dan persen apa adanya).\n'
    '3. Gunakan format berikut, tiap poin diawali "- ", maksimal 3 poin per bagian. '
    'Lewati bagian yang tidak punya fakta.\n'
    'RINGKASAN:\n- ...\nTREN:\n- ...\nPENCAPAIAN:\n- ...\nMASALAH:\n- ...\nTINDAK LANJUT:\n- ...\n'
    f'4. Jika fakta tidak cukup untuk dirangkum, jawab persis: {INSUFFICIENT_MARKER}\n'
    '5. Tanpa pembuka, penutup, atau markdown lain.'
)


def _build_user_prompt(data: ReportFacts) -> str:
    # Fakta disajikan dalam format keluaran yang sama agar SLM cukup
    # menyederhanakan kalimat tiap bagian tanpa mengubah strukturnya.
    lines = [f'Laporan: {data.title}', f'Periode: {data.period}', 'Fakta per bagian:']
    for key, label in CATEGORIES:
        if data.facts[key]:
            lines.append(f'{label}:')
            lines.extend(f'- {text}' for text in data.facts[key])
    sections = ', '.join(label for key, label in CATEGORIES if data.facts[key])
    lines.append('')
    lines.append(
        f'Tulis ulang SEMUA bagian ini sesuai urutan, lengkap dengan judulnya: {sections}. '
        'Gunakan kalimat sederhana dan jangan memindahkan fakta ke bagian lain.'
    )
    return '\n'.join(lines)


def _call_model(system_prompt: str, user_prompt: str) -> str:
    base_url = settings.AI_SUMMARY_BASE_URL.rstrip('/')
    payload = {
        'model': settings.AI_SUMMARY_MODEL,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': 0.1,
        'max_tokens': settings.AI_SUMMARY_MAX_TOKENS,
        'stream': False,
    }
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if settings.AI_SUMMARY_API_KEY:
        headers['Authorization'] = f'Bearer {settings.AI_SUMMARY_API_KEY}'
    req = urllib.request.Request(
        f'{base_url}/chat/completions',
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=settings.AI_SUMMARY_TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        logger.warning('AI summary: model mengembalikan HTTP %s', exc.code)
        if exc.code in (401, 403):
            raise SummaryError('Layanan AI menolak kredensial. Periksa konfigurasi AI_SUMMARY_API_KEY.', 502)
        if exc.code == 404:
            raise SummaryError('Model AI tidak ditemukan. Periksa konfigurasi AI_SUMMARY_MODEL.', 502)
        if exc.code == 429:
            raise SummaryError('Layanan AI sedang sibuk. Coba lagi beberapa saat lagi.', 503)
        raise SummaryError('Layanan AI mengalami kesalahan. Coba lagi nanti.', 502)
    except (socket.timeout, TimeoutError):
        raise SummaryError('Layanan AI terlalu lama merespons. Coba lagi nanti.', 504)
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            raise SummaryError('Layanan AI terlalu lama merespons. Coba lagi nanti.', 504)
        logger.warning('AI summary: layanan tidak dapat dihubungi (%s)', exc.reason)
        raise SummaryError('Layanan AI tidak dapat dihubungi. Pastikan server model berjalan.', 503)
    except (ValueError, UnicodeDecodeError):
        raise SummaryError('Respons layanan AI tidak valid.', 502)

    try:
        content = body['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        raise SummaryError('Respons layanan AI tidak valid.', 502)
    # Model "reasoning" (mis. qwen3) dapat menyertakan blok <think>.
    content = re.sub(r'<think>.*?</think>', '', content or '', flags=re.DOTALL)
    return content.strip()


_RP_PATTERN = re.compile(r'Rp\s?([\d.]+)')


def _unsupported_amounts(text: str, data: ReportFacts) -> List[str]:
    """Nominal Rupiah dalam keluaran model yang tidak ada di fakta."""
    source = ' '.join(t for items in data.facts.values() for t in items)
    known = {m.replace('.', '') for m in _RP_PATTERN.findall(source)}
    return [m for m in _RP_PATTERN.findall(text) if m.rstrip('.').replace('.', '') not in known]


def _norm(text: str) -> str:
    return re.sub(r'[\W_]+', '', text.lower())


_LABELS = {label: key for key, label in CATEGORIES}
_HEADING_PATTERN = re.compile(r'^\[?(' + '|'.join(_LABELS) + r')\]?\s*:\s*(.*)$', re.IGNORECASE)


def _clean_output(text: str, data: ReportFacts) -> str:
    """
    Rapikan keluaran SLM ke format "JUDUL:\\n- poin". Model kecil kadang
    melewatkan bagian; bagian yang punya fakta tetapi tidak ditulis model
    diisi dengan fakta aslinya apa adanya (tetap tanpa informasi baru).
    """
    sections: Dict[str, List[str]] = {}
    current = 'ringkasan'
    for raw in text.splitlines():
        line = raw.strip().replace('**', '')
        line = re.sub(r'^#+\s*', '', line)
        line = re.sub(r'^[-*•]\s*', '', line)
        if not line:
            continue
        heading = _HEADING_PATTERN.match(line)
        if heading:
            current = _LABELS[heading.group(1).upper()]
            line = heading.group(2).strip()
        if line:
            sections.setdefault(current, []).append(line)

    # Buang poin yang identik dengan fakta milik bagian lain (salah tempat).
    owner = {_norm(text): key for key, items in data.facts.items() for text in items}
    for key in sections:
        sections[key] = [item for item in sections[key] if owner.get(_norm(item), key) == key]

    out = []
    for key, label in CATEGORIES:
        items = list(dict.fromkeys(sections.get(key) or data.facts[key]))
        if items:
            out.append(f'{label}:')
            out.extend(f'- {item}' for item in items)
    return '\n'.join(out)


def generate_report_summary(report: str, params: Dict[str, Any]) -> Dict[str, Any]:
    builder = REPORT_BUILDERS.get(report)
    if builder is None:
        raise SummaryError('Jenis laporan tidak dikenali.', 400)

    data = builder(params)
    base = {
        'report': report,
        'title': data.title,
        'period': data.period,
        'facts': data.as_list(),
        'generated_at': timezone.now().isoformat(),
    }
    # Data tidak memadai: jangan panggil model sama sekali.
    if data.is_empty or not data.facts['ringkasan']:
        return {**base, 'status': 'insufficient', 'summary': '', 'message': INSUFFICIENT_MESSAGE, 'model': None}

    if not settings.AI_SUMMARY_ENABLED:
        raise SummaryError('Fitur ringkasan AI belum diaktifkan. Hubungi administrator (AI_SUMMARY_ENABLED).', 503)

    output = _call_model(SYSTEM_PROMPT, _build_user_prompt(data))
    if not output or INSUFFICIENT_MARKER in output:
        return {**base, 'status': 'insufficient', 'summary': '', 'message': INSUFFICIENT_MESSAGE, 'model': settings.AI_SUMMARY_MODEL}

    unsupported = _unsupported_amounts(output, data)
    if unsupported:
        logger.warning('AI summary: keluaran memuat nominal di luar data laporan: %s', unsupported)
        raise SummaryError('Ringkasan yang dihasilkan memuat angka yang tidak ada di laporan, sehingga tidak ditampilkan. Silakan coba lagi.', 502)

    return {**base, 'status': 'ok', 'summary': _clean_output(output, data), 'message': '', 'model': settings.AI_SUMMARY_MODEL}
