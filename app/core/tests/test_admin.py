"""
Tests for custom django admin.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse


class AdminSiteTests(TestCase):
    """ Tests for admin site. """

    def setUp(self):
        """Create a client, super_user and a user."""
        self.admin_user = get_user_model().objects.create_superuser(
            email='admin@example.com',
            password='test123'
        )
        self.client = Client()
        self.client.force_login(self.admin_user)

        self.user = get_user_model().objects.create_user(
            name="TestUserA",
            email='user@example.com',
            password='test123'
        )

    def test_users_list(self):
        """Test that users are listed on the page."""
        url = reverse('admin:core_user_changelist')

        res_page = self.client.get(url)

        self.assertContains(res_page, self.user.email)
        self.assertContains(res_page, self.user.name)

    def test_edit_user_page(self):
        """Test that edit user page works."""
        url = reverse('admin:core_user_change', args=[self.user.id])

        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)

    def test_add_user_page(self):
        """Test that add user page works."""
        url = reverse('admin:core_user_add')

        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
