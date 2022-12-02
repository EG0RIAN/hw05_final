import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import get_object_or_404
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post
from posts.utils import POST_PER_PAGE

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='Тестовый пользователь')
        cls.not_author = User.objects.create_user(
            username='Другой тестовый пользователь'
        )
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='test-slug',
            description='Тестовое описание',
        )

        cls.post = Post.objects.create(
            text='Тест!',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded,
        )
        cls.index = ('posts:index', None)
        cls.group_page = ('posts:group_list', ['test-slug'])
        cls.profile = ('posts:profile', [cls.user])
        cls.profile_another = ('posts:profile', [cls.not_author])
        cls.detail = ('posts:post_detail', [cls.post.id])
        cls.create = ('posts:create_post', None)
        cls.edit = ('posts:post_edit', [cls.post.id])

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_not_author = Client()
        self.authorized_client_not_author.force_login(self.not_author)
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def posts_check_all_fields(self, post):
        """Метод, проверяющий поля поста."""
        with self.subTest(post=post):
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.group.id, self.post.group.id)

    def test_posts_pages_use_correct_template(self):
        """Проверка, использует ли адрес URL соответствующий шаблон."""

        templates_pages_names = (
            (
                'posts/index.html',
                reverse(self.index[0])
            ),
            (
                'posts/group_list.html', reverse(
                    self.group_page[0], kwargs={'slug': self.group.slug}
                )
            ),
            (
                'posts/profile.html', reverse(
                    self.profile[0],
                    args=[self.user]
                )
            ),
            (
                'posts/post_detail.html', reverse(
                    self.detail[0], kwargs={'post_id': self.post.pk}
                )
            ),
            (
                'posts/create_post.html', reverse(
                    self.create[0]
                )
            ),
            (
                'posts/create_post.html',
                reverse(
                    self.edit[0],
                    args=[self.post.pk])
            )
        )

        for template, reverse_name in templates_pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_posts_context_group_list_template(self):
        """
        Проверка, сформирован ли шаблон group_list с
        правильным контекстом.
        Появляется ли пост, при создании на странице его группы.
        """

        template_address, argument = self.group_page
        response = self.authorized_client.get(
            reverse(template_address, args=argument)
        )
        test_group = response.context['group']
        self.posts_check_all_fields(response.context['page_obj'][0])
        self.assertEqual(test_group, self.group)

    def test_posts_context_post_create_template(self):
        """
        Проверка, сформирован ли шаблон post_create с
        правильным контекстом.
        """

        template_address, argument = self.create
        response = self.authorized_client.get(reverse(
            template_address, args=argument)
        )

        form_fields = {
            'group': forms.fields.ChoiceField,
            'text': forms.fields.CharField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_posts_context_post_edit_template(self):
        """
        Проверка, сформирован ли шаблон post_edit с
        правильным контекстом.
        """

        cache.clear()
        template_address, argument = self.edit
        response = self.authorized_client.get(
            reverse(template_address, args=argument)
        )

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_posts_context_profile_template(self):
        """
        Проверка, сформирован ли шаблон profile с
        правильным контекстом.
        """

        template_address, argument = self.profile
        response = self.authorized_client.get(
            reverse(template_address, args=argument)
        )
        author = response.context['author']
        self.assertEqual(author, self.post.author)

        self.posts_check_all_fields(response.context['page_obj'][0])

    def test_posts_context_post_detail_template(self):
        """
        Проверка, сформирован ли шаблон post_detail с
        правильным контекстом.
        """

        template_address, argument = self.detail
        response = self.authorized_client.get(
            reverse(template_address, args=argument)
        )
        self.posts_check_all_fields(response.context['post'])

    def test_post_in_author_profile(self):
        """Пост попадает в профиль к автору, который его написал."""

        template_address, argument = self.profile

        first_object = self.authorized_client.get(reverse(
            template_address, args=argument
        )
        ).context['page_obj'][0]

        self.assertEqual(first_object.author, self.user),
        self.assertEqual(first_object.text, self.post.text),
        self.assertEqual(first_object.group, self.group),

    def test_post_not_in_author_profile(self):
        """Пост не попадает в профиль к автору, который его не написал."""
        template_address, argument = self.profile_another

        first_object = self.authorized_client_not_author.get(reverse(
            template_address, args=argument
        )
        ).context['page_obj'].object_list

        self.assertEqual(len(first_object), 0)

    def test_post_not_another_group(self):
        """Созданный пост не попал в группу,

        для которой не был предназначен."""
        another_group = Group.objects.create(
            title='Дополнительная тестовая группа',
            slug='test-another-slug',
            description='Тестовое описание дополнительной группы',
        )

        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': another_group.slug})
        )

        self.assertEqual(len(response.context['page_obj']), 0)

    def test_add_comment_correct_context(self):
        """Проверка add_comment

        комментарий появляется на странице поста
        комментировать посты может только
        авторизованный пользователь.
        """

        cache.clear()
        tasks_count = Post.objects.count()
        form_data = {
            'post': self.post,
            'author': self.post.author,
            'text': 'Тестовый текст комментария',
            'image': self.uploaded,
        }

        response = self.authorized_client.post(
            reverse('posts:add_comment', args=[self.post.pk]),
            data=form_data
        )

        self.assertEqual(Post.objects.count(), tasks_count)
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=[self.post.pk])
        )
        last_comment = get_object_or_404(Comment, post=self.post)

        self.assertEqual(last_comment.post, self.post)
        self.assertEqual(last_comment.author, self.post.author)
        self.assertEqual(last_comment.text, 'Тестовый текст комментария')
        cache.clear()

    def test_profile_unfollow(self):
        """Авторизованный пользователь может отписываться
            от других пользователей."""
        followers_count = Follow.objects.count()
        Follow.objects.create(user=self.not_author, author=self.user)
        response = self.authorized_client_not_author.post(
            reverse('posts:profile_unfollow', args=[self.user])
        )
        self.assertRedirects(
            response, reverse('posts:profile', args=[self.user])
        )
        self.assertFalse(Follow.objects.all().exists())
        self.assertEqual(
            Follow.objects.count(), followers_count
        )

    def test_profile_follow(self):
        """
        Авторизованный пользователь может подписываться

        на других пользователей.
        """
        followers_count = Follow.objects.count()
        one_more_follower = 1
        response = self.authorized_client_not_author.post(
            reverse('posts:profile_follow', args=[self.user])
        )
        self.assertRedirects(
            response, reverse('posts:profile', args=[self.user])
        )
        self.assertEqual(
            Follow.objects.count(), followers_count + one_more_follower
        )
        self.assertTrue(Follow.objects.filter(
            author=self.user,
            user=self.not_author).exists()
        )


class PostsPaginatorViewsTests(TestCase):
    count_range = POST_PER_PAGE + 3

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='Тестовый пользователь для пагинатора'
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        for count in range(cls.count_range):
            cls.post = Post.objects.create(
                text=f'Тестовый текст поста номер {count}',
                author=cls.user,
                image=cls.uploaded,
            )
        cls.index = ('posts:index', None)
        cls.group_page = ('posts:group_list', ['test-slug'])
        cls.profile = ('posts: profile', [cls.user])

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_post_not_appears_wrong_group(self) -> None:
        """При создании пост не появляется
        в не предназначенной
        для него группе."""

        cache.clear()
        group_two = Group.objects.create(
            title='Тестовая группа №2',
            slug='test-slug-two',
        )
        Post.objects.create(
            text='Тестовый пост №2',
            author=self.user,
            group=group_two,
            image=self.uploaded,
        )
        response = self.authorized_client.get(
            reverse('posts:group_list', args=[group_two.slug])
        )
        first_object = response.context['page_obj'][0]
        self.assertNotEqual(first_object, self.post)

    def test_posts_if_second_page_has_three_records(self):
        """Проверка, содержит ли вторая страница 3 записи."""
        response = self.authorized_client.get(
            reverse(*self.index) + '?page=2'
        )
        self.assertEqual(len(response.context.get('page_obj').object_list), 3)

    def test_cache_index_page(self):
        """Проверка работы кеша"""
        post = Post.objects.create(
            text='Пост под кеш',
            author=self.user)
        content_add = self.authorized_client.get(
            reverse('posts:index')).content
        post.delete()
        content_delete = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertEqual(content_add, content_delete)
        cache.clear()
        content_cache_clear = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertNotEqual(content_add, content_cache_clear)
