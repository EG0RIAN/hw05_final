from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Post, User


class PostCacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.authorized_client = Client()

        cls.authorized_client.force_login(cls.user)
        cls.index = 'posts:index'

    def test_cache_index(self):
        """Проверка хранения и очищения кэша для index."""
        response = self.authorized_client.get(reverse(self.index))
        posts = response.content
        Post.objects.create(
            text='test_new_post',
            author=self.user,
        )
        response_cached = self.authorized_client.get(reverse(self.index))
        old_posts = response_cached.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        response_new_cached = self.authorized_client.get(
            reverse(self.index)
        )
        new_posts = response_new_cached.content
        self.assertNotEqual(old_posts, new_posts)
