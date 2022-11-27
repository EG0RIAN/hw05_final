from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post

User = get_user_model()


class PostsUrlsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Название для теста',
            slug='slug',
            description='Описание для теста',
        )
        cls.author = User.objects.create_user(
            username='Пользователь для теста'
        )
        cls.no_author = User.objects.create_user(
            username='Не зареганный юзер'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Пост для теста',
            group=cls.group,
        )

        cls.index = '/'
        cls.group_page = f'/group/{cls.post.group.slug}/'
        cls.profile = f'/profile/{cls.author}/'
        cls.detail = f'/posts/{cls.post.id}/'
        cls.create = '/create/'
        cls.edit = f'/posts/{cls.post.id}/edit/'

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

        self.no_author_client = Client()
        self.no_author_client.force_login(self.no_author)
        cache.clear()

    def test_urls_guest_user_private(self):
        """Проверка на доступнотсь ссылок
        гостевому пользователю.
        """
        url_names = [
            self.index,
            self.group_page,
            self.profile,
            self.detail,
        ]

        for url in url_names:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page(self):
        """Проверка несуществующих страниц"""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_auth_user_private(self):
        """
        Проверка на доступнотсь ссылок авторизованному пользователю
        """
        url_names = [
            self.index,
            self.group_page,
            self.profile,
            self.detail,
            self.create,
        ]

        for url in url_names:
            with self.subTest(url=url):
                template_address, argument = url
                response = self.no_author_client.get(reverse(
                    template_address, args=argument
                ))
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_auth_user_private(self):
        """
        Проверка на доступнотсь ссылок гостевому пользователю.
        """
        url_names = [
            self.create,
            self.edit,
        ]

        for url in url_names:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertRedirects(response, reverse(
                    'users:login')
                    + "?next=" + url
                )

    def test_post_edit_url(self):
        """Проверка доступности редактирования поста."""

        response = self.authorized_client.get(self.edit)

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_redirect(self):
        """Проверка редиректа редактирования поста
        для неавтора.
        """
        response = self.no_author_client.get(self.edit)

        self.assertRedirects(response, (reverse(
            'posts:post_detail', args=[self.post.id]
        )))

    def test_post_edit_redirect_login(self):
        """Проверка редиректа редактирования поста
        для гостя.
        """
        response = self.guest_client.get(self.edit)
        self.assertRedirects(
            response, reverse(
                'users:login'
            ) + "?next=" + self.edit
        )

    def test_urls_use_correct_template(self):
        """Проверка корректности
        использования шаблонов.
        """
        templates_url_names_public = (
            (
                'posts/index.html',
                self.index
            ),
            (
                'posts/group_list.html',
                self.group_page
            ),
            (
                'posts/profile.html',
                self.profile
            ),
            (
                'posts/post_detail.html',
                self.detail
            ),
            (
                'posts/create_post.html',
                self.create
            ),
            (
                'posts/create_post.html',
                self.edit
            )
        )

        for template, url in templates_url_names_public:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
