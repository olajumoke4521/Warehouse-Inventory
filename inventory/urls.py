from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, StockTransactionViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')
router.register(r'stock-transactions', StockTransactionViewSet, basename='stock-transactions')

urlpatterns = [
    path('', include(router.urls)),
    
]
