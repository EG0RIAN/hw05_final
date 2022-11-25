from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User

User = get_user_model()


class PostsFormsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Новый пользователь')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_posts_forms_create_post(self):
        """Проверка, создает ли форма пост в базе."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост формы',
            'group': self.group.id,
        }

        self.authorized_client.post(
            reverse('posts:create_post'),
            data=form_data,
        )

        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(Post.objects.filter(
            text='Тестовый пост формы',
            group=self.group.id,
            author=self.author.id,
        ).exists())

    def test_posts_forms_edit_post(self):
        """Редачится ли пост."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Текст тестого поста',
            'group': self.group.id,
        }

        self.authorized_client.post(reverse(
            'posts:post_edit',
            kwargs={'post_id': self.post.id},
        ), data=form_data)

        post_endcount = Post.objects.count()
        self.assertEqual(post_count, post_endcount)
        self.assertTrue(Post.objects.filter(
            text=form_data['text'],
            group=self.group.id,
            author=self.author.id,
        ).exists())

    def test_guest_cant_create_post(self):
        """Проверка, не авторизованный
        пользователь не может создать пост."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост формы',
            'author': self.author.id,
            'group': self.group.id,
        }
        self.guest_client.post(
            reverse('posts:create_post'),
            data=form_data,
        )
        self.assertEqual(Post.objects.count(), post_count)
