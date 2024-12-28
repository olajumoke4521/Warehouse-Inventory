from rest_framework import serializers
from .models import Product, StockTransaction, User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'email']

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class StockTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransaction
        fields = ['id', 'product', 'transaction_type', 'quantity', 'timestamp', 'performed_by']
        read_only_fields = ['id', 'timestamp', 'performed_by']
