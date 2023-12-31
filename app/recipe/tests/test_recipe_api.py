"""
Tests for the recipe API
"""

from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Tag,
    Ingredient,
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer
)

RECIPE_LIST_URL = reverse('recipe:recipe-list')
RECIPES_URL = reverse('recipe:recipe-list')


def image_upload_url(recipe_id):
    """Create and return a recipe detail URL."""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def detail_recipe_url(recipe_id):
    """Return the url for the detailed information of a specific recipe"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """Create a sample recipe object and returns it"""
    defaults = {
        'title': 'Sample Recipe',
        'description': 'Sample recipe description',
        'price': Decimal(6.78),
        'time_minutes': 15,
        'link': 'https://example.com'
    }

    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create a user and return it."""
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(RECIPE_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='user@example.com',
            password='test123user'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes."""
        create_recipe(self.user)
        create_recipe(self.user)

        res = self.client.get(RECIPE_LIST_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Test recipe list retrieved is limited to the authenticated user."""
        other_user = create_user(
            email='test1@example.com',
            password='test1example123'
        )
        create_recipe(other_user)
        create_recipe(self.user)

        res = self.client.get(RECIPE_LIST_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_detail(self):
        """Test get recipe detail."""
        recipe = create_recipe(user=self.user)

        url = detail_recipe_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating a recipe"""
        payload = {
            'title': 'Sample Test Recipe',
            'time_minutes': 19,
            'price': Decimal('5.97')
        }
        res = self.client.post(RECIPE_LIST_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])

        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_updates(self):
        """Test partial updates of a recipe."""
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample Recipe',
            link=original_link
        )
        payload = {
            'title': 'New recipe title',
        }
        url = detail_recipe_url(recipe_id=recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update of the recipe."""
        recipe = create_recipe(
            title='Sample recipe',
            user=self.user,
            link='https://example.com/recipe.pdf',
            description='Sample recipe description',
        )
        payload = {
            'title': 'New recipe title',
            'description': 'New recipe description',
            'link': 'https://example.com/new-recipe.pdf',
            'time_minutes': 41,
            'price': Decimal('14.24'),
        }
        url = detail_recipe_url(recipe.id)

        res = self.client.put(url, payload)

        recipe.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)

        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the recipe user returns in an error"""
        new_user = create_user(email='user2@example.com',
                               password='test123user')
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}

        self.client.patch(RECIPES_URL, payload)

        recipe.refresh_from_db()
        self.assertTrue(recipe.user, self.user)

    def test_delete(self):
        """Test deleting a recipe successful"""
        recipe = create_recipe(user=self.user)

        url = detail_recipe_url(recipe.id)
        res = self.client.delete(url)

        self.assertTrue(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe_error(self):
        """Test trying to delete other user's recipes results in an error."""
        new_user = create_user(
            email='testuser2@example.com', password='test123')
        recipe = create_recipe(user=new_user)

        url = detail_recipe_url(recipe.id)
        res = self.client.delete(url)

        self.assertTrue(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags."""
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)

        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tag."""
        tag_indian = Tag.objects.create(user=self.user, name="Indian")
        payload = {
            'title': 'Pongal',
            'time_minutes': 60,
            'price': Decimal(4.50),
            'tags': [{'name': 'Indian'}, {'name': 'Breakfast'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())

        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating tag when updating a recipe."""
        recipe = create_recipe(user=self.user)
        payload = {'tags': [{'name': 'Lunch'}]}

        url = detail_recipe_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe."""
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_recipe_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_existing_tag(self):
        """Test clearing existing tags."""
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        payload = {'tags': []}
        url = detail_recipe_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Create recipe with new ingredients."""
        payload = {
            'title': 'Salt Pepper Bread',
            'price': Decimal('2.4'),
            'time_minutes': 6,
            'ingredients': [{'name': 'Salt'}, {'name': 'Pepper'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipes[0].ingredients.count(), 2)

        for ingredient in payload['ingredients']:
            exists = recipes[0].ingredients.filter(
                name=ingredient['name'], user=self.user)
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredients(self):
        """Test creaing a recipe with new ingredients."""

        ingredient = Ingredient.objects.create(
            user=self.user, name='Cauliflower')
        payload = {
            'title': 'Cauliflower Tacos',
            'time_minutes': 34,
            'price': Decimal('8.92'),
            'ingredients': [{'name': 'Cauliflower'}, {'name': 'Salt'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)

        self.assertTrue(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())

        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'], user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_multiple_new_ingredients_with_update(self):
        """Test creating multiple new ingredients with recipe update."""
        payload = {'ingredients': [{'name': 'Salt'}, {'name': 'Pepper'}]}
        recipe = create_recipe(user=self.user)
        url = detail_recipe_url(recipe.id)

        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 2)

        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                user=self.user, name=ingredient['name']).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating an ingredient when updating a recipe."""
        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name': 'Limes'}]}
        url = detail_recipe_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(
            user=self.user, name='Limes')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_update(self):
        """Test assigning an existing ingredient when updating a recipe"""
        ingredient_to_clear = Ingredient.objects.create(
            user=self.user, name='Pepper')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient_to_clear)

        ingredient_to_add = Ingredient.objects.create(
            user=self.user, name='Chilly')
        payload = {'ingredients': [{'name': 'Chilly'}]}
        url = detail_recipe_url(recipe.id)

        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient_to_add, recipe.ingredients.all())
        self.assertNotIn(ingredient_to_clear, recipe.ingredients.all())

    def test_clear_ingredients(self):
        """"Test clearing ingredients on update."""
        ingredient = Ingredient.objects.create(
            user=self.user, name='Pepper')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detail_recipe_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        """Test filtering recipes by tags."""
        r1 = create_recipe(user=self.user, title='Curry')
        r2 = create_recipe(user=self.user, title='Rice pulao')
        ingredient1 = Tag.objects.create(user=self.user, name='Turmeric')
        ingredient2 = Tag.objects.create(user=self.user, name='Carbs')

        r1.tags.add(ingredient1)
        r2.tags.add(ingredient2)
        r3 = create_recipe(user=self.user, title='Curd')
        params = {'tags': f'{ingredient1.id},{ingredient2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        """Test filtering recipes by ingredients."""
        r1 = create_recipe(user=self.user, title='Curry')
        r2 = create_recipe(user=self.user, title='Rice pulao')
        ingredient1 = Ingredient.objects.create(
            user=self.user, name='Milk')
        ingredient2 = Ingredient.objects.create(
            user=self.user, name='Rice')

        r1.ingredients.add(ingredient1)
        r2.ingredients.add(ingredient2)
        r3 = create_recipe(user=self.user, title='Curd')
        params = {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    """Tests for the image upload API."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        """Runs after every test"""
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='jpeg')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploAding an invalid image gives bad request"""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
