from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from config.permissions import StrictRoleBasedAccess
from finance.reports import (
    generate_balance_sheet,
    generate_product_sales_report,
    generate_sales_trends,
    generate_annual_report,
    generate_pie_chart_analytics
)


class FinancialReportsViewSet(viewsets.ViewSet):
    """
    Financial & Analytical Reports API:
    - Balance Sheet (Neraca)
    - Product Sales & Margin Report
    - 12-Month Sales Trends
    - Annual Financial Summary
    - Brand & Package Size Pie Chart Analytics
    Accessible to Accounting, Finance, Admin, Direktur, and Stakeholders.
    """
    permission_classes = [permissions.IsAuthenticated, StrictRoleBasedAccess]

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
        return Response({'year': year_val, 'trends': trends}, status=status.HTTP_200_OK)

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

