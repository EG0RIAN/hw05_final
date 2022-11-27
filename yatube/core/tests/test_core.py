from django.test import Client, TestCase

from posts.models import User


class CoreViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='HasntName')

    def test_urls_uses_correct_template(self):
        """URL использует соответствующий шаблон."""

        response = self.guest_client.get('/unexisting_page/')
        self.assertTemplateUsed(response, 'core/404.html')
