"""
Views for the recipe API
"""

from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import Recipe
from recipe import serializers


class RecipeViewSet(viewsets.ModelViewSet):
    """View for manage recipe api"""
    queryset = Recipe.objects.all()
    serializer_class = serializers.RecipeSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Retrieve recipes for authenticated users."""
        return self.queryset.filter(user=self.request.user).order_by('-id')
