from http import HTTPStatus

from django import forms
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Comment, Group, Post

User = get_user_model()


class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Тестовый пользователь1')
        cls.user2 = User.objects.create_user(username='Тестовый пользователь2')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='test-slug',
            description='Тестовое описание',
        )

        cls.post = Post.objects.create(
            text='Тест!',
            author=cls.user,
            group=cls.group,
        )
        cls.index = ('posts:index', None)
        cls.group_page = ('posts:group_list', ['test-slug'])
        cls.profile = ('posts:profile', [cls.user])
        cls.profile2 = ('posts:profile', [cls.user2])
        cls.detail = ('posts:post_detail', [cls.post.id])
        cls.create = ('posts:create_post', None)
        cls.edit = ('posts:post_edit', [cls.post.id])

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user2)

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
        template_address, argument = self.edit
        response = self.authorized_client.get(
            reverse(template_address, args=argument)
        )

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
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
        """Пост попадает в профиль к автору, который его написал"""
        template_address, argument = self.profile
        first_object = self.authorized_client.get(reverse(
            template_address, args=argument
        )
        ).context['page_obj'][0]
        self.assertEqual(first_object.author, self.user),
        self.assertEqual(first_object.text, self.post.text),
        self.assertEqual(first_object.group, self.group),

    def test_post_not_in_author_profile(self):
        """Пост не попадает в профиль к автору, который его не написал;"""
        template_address, argument = self.profile2
        first_object = self.authorized_client2.get(reverse(
            template_address, args=argument
        )
        ).context['page_obj'].object_list
        self.assertEqual(len(first_object), 0)

    def test_post_not_another_group(self):
        """Созданный пост не попал в группу, для которой не был предназначен"""
        another_group = Group.objects.create(
            title='Дополнительная тестовая группа',
            slug='test-another-slug',
            description='Тестовое описание дополнительной группы',
        )
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': another_group.slug})
        )
        self.assertEqual(len(response.context['page_obj']), 0)


class PostsPaginatorViewsTests(TestCase):
    count_range = 13

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Тестовый пользователь')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.post_list = Post.objects.filter(
            author__following__user=cls.user
        ).all()
        for count in range(cls.count_range):
            cls.post = Post.objects.create(
                text=f'Тестовый текст поста номер {count}',
                author=cls.user,
            )
        cls.index = ('posts:index', None)
        cls.group_page = ('posts:group_list', ['test-slug'])
        cls.profile = ('posts: profile', [cls.user])

    def test_post_not_appears_wrong_group(self) -> None:
        '''При создании пост не появляется в не предназначенной
        для него группе'''
        group_two = Group.objects.create(
            title='Тестовая группа №2',
            slug='test-slug-two',
        )
        Post.objects.create(
            text='Тестовый пост №2',
            author=self.user,
            group=group_two,
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

    def test_add_comment_correct_context(self):
        """Проверка add_comment
        комментарий появляется на странице поста
        комментировать посты может только авторизованный пользователь
        """
        tasks_count = Post.objects.count()
        form_data = {
            'post': self.post,
            'author': self.post.author,
            'text': 'Тестовый текст комментария'
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

    def test_follow(self):
        """Проверка авторизованный пользователь может
        подписываться на других пользователей """

        self.authorized_client.get(f'/profile/{self.user}/follow/')
        response = self.authorized_client.get('/follow/')

        for post in self.post_list:
            self.assertEqual(response.context.get('post'), post)

    def test_unfollow(self):
        """Проверка авторизованный пользователь может
        удалять других пользователей из подписок """

        self.authorized_client.get(f'/profile/{self.user}/unfollow/')
        response = self.authorized_client.get('/follow/')

        for post in self.post_list:
            self.assertEqual(response.context.get('post'), post)

    def test_check_correct_followed(self):
        """Проверка Ленты постов авторов
        Новая запись пользователя появляется в ленте
        тех, кто на него подписан"""

        response = self.authorized_client.get('/follow/')

        for post in self.post_list:
            self.assertEqual(response.context.get('post'), post)

    def test_check_correct_unfollowed(self):
        """Проверка Ленты постов авторов
        В ленте подписок нет лишних постов"""

        response = self.authorized_client.get('/follow/')

        self.assertEqual(response.context.get('post'), None)
