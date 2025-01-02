from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Warehouse, Customer, Product, WarehouseStock,
    StockTransaction
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_staff')

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class WarehouseStockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    
    class Meta:
        model = WarehouseStock
        fields = '__all__'

class StockTransactionSerializer(serializers.ModelSerializer):
    source_warehouse_name = serializers.CharField(source='source_warehouse.name', read_only=True)
    destination_warehouse_name = serializers.CharField(source='destination_warehouse.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    performed_by_username = serializers.CharField(source='performed_by.username', read_only=True)

    class Meta:
        model = StockTransaction
        fields = '__all__'
        read_only_fields = ('performed_by',)

    def validate(self, attrs):
        # First do the basic validation
        transaction_type = attrs.get('transaction_type')
        source_warehouse = attrs.get('source_warehouse')
        destination_warehouse = attrs.get('destination_warehouse')
        customer = attrs.get('customer')
        
        # Get the user from the context
        user = self.context['request'].user

        # Only admin can skip warehouse access check
        if not user.is_staff:
            # For WW transfers, check access to both warehouses
            if transaction_type == 'WW':
                if not source_warehouse or not destination_warehouse:
                    raise serializers.ValidationError('Both warehouses are required for warehouse-to-warehouse transfer')
                if user not in source_warehouse.authorized_users.all():
                    raise serializers.ValidationError('You do not have access to the source warehouse')
                if user not in destination_warehouse.authorized_users.all():
                    raise serializers.ValidationError('You do not have access to the destination warehouse')

            # For WC transfers, check access to source warehouse
            elif transaction_type == 'WC':
                if not source_warehouse or not customer:
                    raise serializers.ValidationError('Source warehouse and customer are required for warehouse-to-customer transfer')
                if user not in source_warehouse.authorized_users.all():
                    raise serializers.ValidationError('You do not have access to the source warehouse')

            # For CW transfers, check access to destination warehouse
            elif transaction_type == 'CW':
                if not destination_warehouse or not customer:
                    raise serializers.ValidationError('Destination warehouse and customer are required for customer-to-warehouse transfer')
                if user not in destination_warehouse.authorized_users.all():
                    raise serializers.ValidationError('You do not have access to the destination warehouse')

        return attrs
    
    def create(self, validated_data):
        # Get the user from context and add it to validated_data
        validated_data['performed_by'] = self.context['request'].user
        return super().create(validated_data)