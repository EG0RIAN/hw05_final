import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Group, Post, User

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsFormsTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

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

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

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

    def test_add_comment(self) -> None:
        """Проверка формы комментария."""
        self.comments_count = Comment.objects.count()
        one_more_comment = 1

        form_data = {
            'text': 'Тестовый комментарий'
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=[self.post.pk]),
            data=form_data,
            follow=True,
        )

        self.assertRedirects(
            response, reverse('posts:post_detail', args=[self.post.pk])
        )
        self.assertEqual(
            Comment.objects.count(), self.comments_count + one_more_comment
        )
        self.assertTrue(Comment.objects.filter(
            author=self.author,
            post=self.post.pk,
            text=form_data['text']).exists()
        )
