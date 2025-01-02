from django.shortcuts import render
from django.core.cache import cache
from rest_framework import viewsets, status, generics, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import logout
from django.db.models import Q, F, Count, Prefetch
from django.shortcuts import get_object_or_404
from .models import (
    Warehouse, Customer, Product, WarehouseStock,
     StockTransaction
)
from .serializers import (
    WarehouseSerializer, CustomerSerializer,
    ProductSerializer, WarehouseStockSerializer,
    StockTransactionSerializer
)
from .permissions import IsAdminUser, HasWarehouseAccess
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError

class LoginView(TokenObtainPairView):
    pass

class LogoutView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, *args, **kwargs):
        logout(request)
        return Response({'detail': 'Successfully logged out.'})

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Warehouse.objects.all()
        return self.request.user.authorized_warehouses.all()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class WarehouseStockViewSet(viewsets.ModelViewSet):
    queryset = WarehouseStock.objects.all()
    serializer_class = WarehouseStockSerializer
    permission_classes = [IsAuthenticated, HasWarehouseAccess]

    def get_queryset(self):
        queryset = WarehouseStock.objects.all()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                warehouse__authorized_users=self.request.user
            )
        
        # Filter by warehouse if specified
        warehouse_id = self.request.query_params.get('warehouse', None)
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        
        # Filter by product if specified
        product_id = self.request.query_params.get('product', None)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
            
        return queryset.select_related('warehouse', 'product')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated(), HasWarehouseAccess()]


class StockTransactionViewSet(viewsets.ModelViewSet):
    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def validate_date_range(self, start_date, end_date):
        if bool(start_date) != bool(end_date):
            raise serializers.ValidationError("Both start_date and end_date are required")
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date cannot be after end_date")

    def get_authorized_warehouses(self):
        user = self.request.user
        if user.is_staff:
            return Warehouse.objects.all()
        return user.authorized_warehouses.all()

    def get_queryset(self):
        queryset = StockTransaction.objects.select_related(
            'source_warehouse',
            'destination_warehouse',
            'customer',
            'product',
            'performed_by'
        ).prefetch_related(
            'source_warehouse__authorized_users',
            'destination_warehouse__authorized_users'
        )
        
        user = self.request.user
        params = self.request.query_params
        warehouse_id = params.get('warehouse')
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        transaction_type = params.get('transaction_type')
        
        # Validate date range if provided
        if start_date or end_date:
            self.validate_date_range(start_date, end_date)

        # Base query for authorized warehouses
        authorized_warehouses = self.get_authorized_warehouses()
        
        if not user.is_staff:
            queryset = queryset.filter(
                Q(source_warehouse__in=authorized_warehouses) |
                Q(destination_warehouse__in=authorized_warehouses)
            )

        # Apply specific warehouse filter if requested
        if warehouse_id:
            if int(warehouse_id) not in authorized_warehouses.values_list('id', flat=True):
                raise serializers.ValidationError("You don't have access to this warehouse")
            queryset = queryset.filter(
                Q(source_warehouse_id=warehouse_id) |
                Q(destination_warehouse_id=warehouse_id)
            )
        
        # Apply additional filters
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
            
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        
        return queryset.order_by('-created_at')

    def get_warehouse_stats(self, queryset):
        authorized_warehouses = self.get_authorized_warehouses()
        cache_key = f'warehouse_stats_{self.request.user.id}'
        stats = cache.get(cache_key)
        
        if stats is None:
            stats = {}
            for warehouse in authorized_warehouses:
                warehouse_transactions = queryset.filter(
                    Q(source_warehouse=warehouse) |
                    Q(destination_warehouse=warehouse)
                )
                
                stats[warehouse.name] = {
                    'id': warehouse.id,
                    'Entry': warehouse_transactions.filter(
                        destination_warehouse=warehouse
                    ).count(),
                    'Exit': warehouse_transactions.filter(
                        source_warehouse=warehouse
                    ).count(),
                    'products': WarehouseStock.objects.filter(
                        warehouse=warehouse
                    ).count(),
                    'low_stock_items': WarehouseStock.objects.filter(
                        warehouse=warehouse,
                        quantity__lte=F('product__minimum_stock')
                    ).count()
                }
            cache.set(cache_key, stats, timeout=300)  # 5 minutes
        
        return stats

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        warehouse_stats = self.get_warehouse_stats(queryset)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data = {
                'warehouse_stats': warehouse_stats,
                **response.data
            }
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'warehouse_stats': warehouse_stats,
            'results': serializer.data
        })

    def perform_create(self, serializer):
        user = self.request.user
        data = self.request.data
        source_id = data.get('source_warehouse')
        dest_id = data.get('destination_warehouse')
        
        # Verify warehouse access
        if source_id:
            source_warehouse = get_object_or_404(Warehouse, id=source_id)
            if not user.is_staff and user not in source_warehouse.authorized_users.all():
                raise serializers.ValidationError(
                    {'source_warehouse': 'You do not have access to this warehouse'}
                )
                
        if dest_id:
            dest_warehouse = get_object_or_404(Warehouse, id=dest_id)
            if not user.is_staff and user not in dest_warehouse.authorized_users.all():
                raise serializers.ValidationError(
                    {'destination_warehouse': 'You do not have access to this warehouse'}
                )
        
        serializer.save(performed_by=user)

    @action(detail=False, methods=['get'])
    def available_warehouses(self, request):
        """Return list of warehouses user has access to"""
        warehouses = self.get_authorized_warehouses()
        serializer = WarehouseSerializer(warehouses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def warehouse_summary(self, request):
        """Detailed summary of warehouse statistics"""
        warehouse_id = request.query_params.get('warehouse')
        if warehouse_id and not self.get_authorized_warehouses().filter(id=warehouse_id).exists():
            return Response(
                {'error': 'You do not have access to this warehouse'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        queryset = self.get_queryset()
        if warehouse_id:
            queryset = queryset.filter(
                Q(source_warehouse_id=warehouse_id) |
                Q(destination_warehouse_id=warehouse_id)
            )
            
        summary = {
            'transaction_types': queryset.values('transaction_type').annotate(
                count=Count('id')
            ),
            'transfer_types': queryset.values('transfer_type').annotate(
                count=Count('id')
            ),
            'top_products': queryset.values(
                'product__name'
            ).annotate(
                count=Count('id')
            ).order_by('-count')[:10],
            'warehouse_stats': self.get_warehouse_stats(queryset)
        }
        
        return Response(summary)