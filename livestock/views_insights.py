from django.db.models import Count, Sum, F, DecimalField, Value, ExpressionWrapper
from django.db.models.functions import TruncMonth, Coalesce
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import datetime, timedelta
from .models import AMURecord, Drug, FeedRecord, YieldRecord
from .permissions import IsFarmMember


class AMUInsightsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsFarmMember]

    @action(detail=False, methods=['GET'], url_path='chart-data')
    def chart_data(self, request):
        livestock_id = request.query_params.get('livestock_id')
        if not livestock_id:
            return Response({"error": "Livestock ID is required"}, status=400)


        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)


        amu_records = AMURecord.objects.filter(
            health_record__livestock_id=livestock_id,
            health_record__event_date__gte=start_date,
            health_record__event_date__lte=end_date
        )


        monthly_usage = (
            amu_records
            .annotate(month=TruncMonth('health_record__event_date'))
            .values('month', 'drug__name')
            .annotate(count=Count('id'))
            .order_by('month', 'drug__name')
        )


        chart_data = {
            'labels': [],
            'datasets': []
        }


        drugs = Drug.objects.filter(
            id__in=amu_records.values_list('drug_id', flat=True)
        ).distinct()
        drug_datasets = {drug.name: [] for drug in drugs}


        months = []
        current = start_date
        while current <= end_date:
            month_str = current.strftime('%Y-%m')
            months.append(month_str)
            for drug_data in drug_datasets.values():
                drug_data.append(0)
            current = (current.replace(day=1) + timedelta(days=32)).replace(day=1)


        for record in monthly_usage:
            month_str = record['month'].strftime('%Y-%m')
            if month_str in months:
                month_index = months.index(month_str)
                drug_name = record['drug__name']
                if drug_name in drug_datasets:
                    drug_datasets[drug_name][month_index] = record['count']


        formatted_labels = [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in months]
        chart_data['labels'] = formatted_labels


        colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
            '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF9F40'
        ]


        for i, (drug_name, counts) in enumerate(drug_datasets.items()):
            dataset = {
                'label': drug_name,
                'data': counts,
                'backgroundColor': colors[i % len(colors)],
                'borderColor': colors[i % len(colors)],
                'borderWidth': 1,
                'fill': False
            }
            chart_data['datasets'].append(dataset)

        return Response({
            'chart_data': chart_data,
            'summary': {
                'total_treatments': amu_records.count(),
                'unique_drugs': len(drugs),
                'time_period': f"{formatted_labels[0]} to {formatted_labels[-1]}"
            }
        })


class FeedInsightsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsFarmMember]

    @action(detail=False, methods=['GET'], url_path='chart-data')
    def chart_data(self, request):
        livestock_id = request.query_params.get('livestock_id')
        if not livestock_id:
            return Response({"error": "Livestock ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        qs = FeedRecord.objects.filter(
            livestock_id=livestock_id,
            date__gte=start_date,
            date__lte=end_date,
        )


        price_decimal = Coalesce(
            'price_per_kg',
            F('feed__cost_per_kg'),
            Value(0),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
        cost_expr = ExpressionWrapper(
            F('quantity_kg') * price_decimal,
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
        monthly_spend = (
            qs.annotate(month=TruncMonth('date'))
              .annotate(cost=cost_expr)
              .values('month')
              .annotate(total_spend=Sum('cost'))
              .order_by('month')
        )


        breakdown = (
            qs.annotate(month=TruncMonth('date'))
              .annotate(cost=cost_expr)
              .values('month', 'feed__name', 'feed_type')
              .annotate(total_spend=Sum('cost'))
              .order_by('month', 'feed__name', 'feed_type')
        )


        months = []
        current = start_date
        while current <= end_date:
            months.append(current.strftime('%Y-%m'))
            current = (current.replace(day=1) + timedelta(days=32)).replace(day=1)


        spend_map = {m['month'].strftime('%Y-%m'): float(m['total_spend'] or 0) for m in monthly_spend}
        spend_series = [spend_map.get(m, 0.0) for m in months]


        by_feed = {}
        for row in breakdown:
            month_key = row['month'].strftime('%Y-%m')
            feed_name = row['feed__name'] or row['feed_type'] or 'Unknown'
            by_feed.setdefault(feed_name, {m: 0.0 for m in months})
            by_feed[feed_name][month_key] = float(row['total_spend'] or 0)

        colors = ['#1976d2','#2e7d32','#ed6c02','#d32f2f','#6d4c41','#00897b','#7b1fa2','#5c6bc0']
        datasets = []
        for i, (name, month_values) in enumerate(by_feed.items()):
            datasets.append({
                'label': name,
                'data': [month_values[m] for m in months],
                'backgroundColor': colors[i % len(colors)],
                'borderColor': colors[i % len(colors)],
                'stack': 'feed',
            })

        formatted_labels = [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in months]

        return Response({
            'spend_chart': {
                'labels': formatted_labels,
                'datasets': [{
                    'label': 'Total Spend (₦)',
                    'data': spend_series,
                    'backgroundColor': '#1976d2',
                    'borderColor': '#1976d2',
                    'fill': False,
                }]
            },
            'breakdown_chart': {
                'labels': formatted_labels,
                'datasets': datasets
            },
            'summary': {
                'total_spend': round(sum(spend_series), 2),
                'avg_monthly_spend': round(sum(spend_series) / (len(spend_series) or 1), 2),
                'time_period': f"{formatted_labels[0]} to {formatted_labels[-1]}"
            }
        })


class YieldInsightsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsFarmMember]

    @action(detail=False, methods=['GET'], url_path='chart-data')
    def chart_data(self, request):
        livestock_id = request.query_params.get('livestock_id')
        yield_type = request.query_params.get('yield_type')
        if not livestock_id:
            return Response({"error": "Livestock ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        qs = YieldRecord.objects.filter(
            livestock_id=livestock_id,
            date__gte=start_date,
            date__lte=end_date,
        )
        if yield_type:
            qs = qs.filter(yield_type=yield_type)

        monthly_yield = (
            qs.annotate(month=TruncMonth('date'))
              .values('month', 'unit', 'yield_type')
              .annotate(total_qty=Sum('quantity'))
              .order_by('month', 'yield_type')
        )

        months = []
        current = start_date
        while current <= end_date:
            months.append(current.strftime('%Y-%m'))
            current = (current.replace(day=1) + timedelta(days=32)).replace(day=1)


        by_type = {}
        unit = None
        for row in monthly_yield:
            month_key = row['month'].strftime('%Y-%m')
            ytype = row['yield_type']
            unit = unit or row['unit']
            by_type.setdefault(ytype, {m: 0.0 for m in months})
            by_type[ytype][month_key] = float(row['total_qty'] or 0)

        colors = ['#36A2EB', '#FF6384', '#4BC0C0', '#9966FF', '#FF9F40']
        datasets = []
        for i, (name, month_values) in enumerate(by_type.items()):
            datasets.append({
                'label': f"{name} ({unit})" if unit else name,
                'data': [month_values[m] for m in months],
                'backgroundColor': colors[i % len(colors)],
                'borderColor': colors[i % len(colors)],
                'fill': False,
            })

        formatted_labels = [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in months]

        return Response({
            'labels': formatted_labels,
            'datasets': datasets,
            'summary': {
                'total_yield': round(sum([sum(v.values()) for v in by_type.values()]), 2),
                'types': list(by_type.keys()),
                'time_period': f"{formatted_labels[0]} to {formatted_labels[-1]}"
            }
        })
