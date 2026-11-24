from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from django.utils import timezone
from core.permissions import DEFAULT_PERMISSIONS, MANAGEMENT
from finance.reports.sales_reports import sales_by_brand_and_size
from finance.reports import (
    generate_balance_sheet,
    generate_product_sales_report,
    generate_sales_trends,
    generate_annual_report,
    generate_pie_chart_analytics
)
from finance.services.report_summary_service import REPORT_BUILDERS, SummaryError, generate_report_summary


class AISummaryThrottle(UserRateThrottle):
    """Batas panggilan ringkasan AI per pengguna (THROTTLE_AI_SUMMARY)."""
    scope = 'ai_summary'


class FinancialReportsViewSet(viewsets.ViewSet):
    """
    Financial & Analytical Reports API:
    - Balance Sheet (Neraca)
    - Product Sales & Margin Report
    - 12-Month Sales Trends
    - Annual Financial Summary
    - Brand & Package Size Pie Chart Analytics
    Akses: Direktur, Admin, Stakeholder (read-only). Gudang ditolak (403).
    """
    permission_classes = DEFAULT_PERMISSIONS
    role_access = {'read': MANAGEMENT}

    @action(detail=False, methods=['get'], url_path='balance-sheet')
    def balance_sheet(self, request):
        as_of = request.query_params.get('as_of_date')
        if as_of:
            try:
                date_val = timezone.datetime.strptime(as_of, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            date_val = timezone.now().date()

        report = generate_balance_sheet(date_val)
        return Response(report, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='product-sales')
    def product_sales(self, request):
        year = request.query_params.get('year')
        year_val = int(year) if year and year.isdigit() else timezone.now().year
        report = generate_product_sales_report(year_val)
        return Response(report, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='sales-trends')
    def sales_trends(self, request):
        year = request.query_params.get('year')
        year_val = int(year) if year and year.isdigit() else timezone.now().year
        trends = generate_sales_trends(year_val)
        return Response({'year': year_val, 'trends': trends, 'sales_mix': sales_by_brand_and_size(year_val)})

    @action(detail=False, methods=['get'], url_path='annual-report')
    def annual_report(self, request):
        year = request.query_params.get('year')
        year_val = int(year) if year and year.isdigit() else timezone.now().year
        report = generate_annual_report(year_val)
        return Response(report, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='pie-charts')
    def pie_charts(self, request):
        analytics = generate_pie_chart_analytics()
        return Response(analytics, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['get'],
        url_path='summary',
        throttle_classes=[AISummaryThrottle],
    )
    def summary(self, request):
        """
        Ringkasan AI (SLM) untuk laporan yang sedang dibuka.
        Query: report=<sales-trends|product-sales|annual|balance-sheet|pie-charts>,
        year=YYYY (laporan tahunan) atau as_of_date=YYYY-MM-DD (neraca).
        """
        report = request.query_params.get('report', '')
        if report not in REPORT_BUILDERS:
            return Response(
                {'error': f"Parameter 'report' wajib salah satu dari: {', '.join(REPORT_BUILDERS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        params = {}
        if report == 'balance-sheet':
            as_of = request.query_params.get('as_of_date')
            try:
                params['as_of_date'] = (
                    timezone.datetime.strptime(as_of, '%Y-%m-%d').date() if as_of else timezone.localdate()
                )
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        elif report != 'pie-charts':
            year = request.query_params.get('year')
            params['year'] = int(year) if year and year.isdigit() else timezone.now().year

        try:
            result = generate_report_summary(report, params)
        except SummaryError as exc:
            return Response({'error': exc.message}, status=exc.status_code)
        return Response(result, status=status.HTTP_200_OK)
