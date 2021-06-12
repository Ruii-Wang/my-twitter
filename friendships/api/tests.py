from testing.testcases import TestCase
from rest_framework.test import APIClient
from friendships.models import Friendship
from friendships.api.paginations import FriendshipPagination

FOLLOW_URL = '/api/friendships/{}/follow/'
UNFOLLOW_URL = '/api/friendships/{}/unfollow/'
FOLLOWERS_URL = '/api/friendships/{}/followers/'
FOLLOWINGS_URL = '/api/friendships/{}/followings/'

class FriendshipApiTests(TestCase):

    def setUp(self):
        # 匿名用户 其创建已经挪到testcase当中
        # self.anonymous_client = APIClient()

        # 登录用户
        self.ming = self.create_user('ming')
        self.ming_client = APIClient()
        self.ming_client.force_authenticate(self.ming)

        self.rui = self.create_user('rui')
        self.rui_client = APIClient()
        self.rui_client.force_authenticate(self.rui)

        # create followings and followers for rui
        for i in range(2):
            follower = self.create_user(
                'ming_follower{}'.format(i),
            )
            Friendship.objects.create(from_user=follower, to_user=self.ming)
        for i in range(3):
            following = self.create_user(
                'ming_following{}'.format(i),
            )
            Friendship.objects.create(from_user=self.ming, to_user=following)

    def test_follow(self):
        url = FOLLOW_URL.format(self.rui.id)

        # 需要登录才能follow别人
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 403)

        # 要用post来follow
        response = self.rui_client.get(url)
        self.assertEqual(response.status_code, 405)

        # 不能follow自己
        response = self.rui_client.post(url)
        self.assertEqual(response.status_code, 400)

        # follow成功
        response = self.ming_client.post(url)
        self.assertEqual(response.status_code, 201)
        self.assertEqual('created_at' in response.data, True)
        self.assertEqual('user' in response.data, True)
        self.assertEqual(response.data['user']['id'], self.rui.id)
        self.assertEqual(response.data['user']['username'], self.rui.username)

        # 重复follow会报错
        response = self.ming_client.post(url)
        self.assertEqual(response.status_code, 400)

        # 反向关注会创建新的数据
        count = Friendship.objects.count()
        response = self.rui_client.post(FOLLOW_URL.format(self.ming.id))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Friendship.objects.count(), count+1)

        # follow non-exist user
        response = self.ming_client.post(FOLLOW_URL.format(0))
        self.assertEqual(response.status_code, 404)

    def test_unfollow(self):
        url = UNFOLLOW_URL.format(self.rui.id)

        # 需要登录才能unfollow
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 403)

        # 需要采用post
        response = self.ming_client.get(url)
        self.assertEqual(response.status_code, 405)

        # 自己不能unfollow自己
        response = self.rui_client.post(url)
        self.assertEqual(response.status_code, 400)

        # unfollow成功
        Friendship.objects.create(from_user=self.ming, to_user=self.rui)
        count = Friendship.objects.count()
        response = self.ming_client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted'], 1)
        self.assertEqual(Friendship.objects.count(), count-1)

        # 重复unfollow
        count = Friendship.objects.count()
        response = self.ming_client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted'], 0)
        self.assertEqual(Friendship.objects.count(), count)

    def test_following(self):
        url = FOLLOWINGS_URL.format(self.ming.id)

        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 405)

        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)
        ts0 = response.data['results'][0]['created_at']
        ts1 = response.data['results'][1]['created_at']
        ts2 = response.data['results'][2]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(ts1 > ts2, True)
        self.assertEqual(
            response.data['results'][0]['user']['username'],
            'ming_following2'
        )
        self.assertEqual(
            response.data['results'][1]['user']['username'],
            'ming_following1'
        )
        self.assertEqual(
            response.data['results'][2]['user']['username'],
            'ming_following0'
        )

    def test_follower(self):
        url = FOLLOWERS_URL.format(self.ming.id)

        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 405)

        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        ts0 = response.data['results'][0]['created_at']
        ts1 = response.data['results'][1]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(
            response.data['results'][0]['user']['username'],
            'ming_follower1'
        )
        self.assertEqual(
            response.data['results'][1]['user']['username'],
            'ming_follower0'
        )

    def test_followers_pagination(self):
        max_page_size = FriendshipPagination.max_page_size
        page_size = FriendshipPagination.page_size
        for i in range(page_size * 2):
            follower = self.create_user('rui_followers{}'.format(i))
            Friendship.objects.create(from_user = follower, to_user = self.rui)
            if follower.id % 2 == 1:
                Friendship.objects.create(from_user = self.ming, to_user = follower)
        url = FOLLOWERS_URL.format(self.rui.id)
        self._test_friendship_pagination(url, page_size, max_page_size)

        # anonymous has not followed any users
        response = self.anonymous_client.get(url, {'page': 1})
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], False)

        # ming has followed users with odd id
        response = self.ming_client.get(url, {'page': 1})
        for result in response.data['results']:
            has_followed = (result['user']['id'] % 2 == 1)
            self.assertEqual(result['has_followed'], has_followed)

    def test_followings_pagination(self):
        max_page_size = FriendshipPagination.max_page_size
        page_size = FriendshipPagination.page_size
        for i in range(page_size * 2):
            following = self.create_user('rui__following{}'.format(i))
            Friendship.objects.create(from_user=self.rui, to_user=following)
            if following.id % 2 == 0:
                Friendship.objects.create(from_user=self.ming, to_user=following)
        url = FOLLOWINGS_URL.format(self.rui.id)
        self._test_friendship_pagination(url, page_size, max_page_size)

        # anonymous has not followed any users
        response = self.anonymous_client.get(url, {'page': 1})
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], False)

        # ming has followed users with even id
        response = self.ming_client.get(url, {'page': 1})
        for result in response.data['results']:
            has_followed = (result['user']['id'] % 2 == 0)
            self.assertEqual(result['has_followed'], has_followed)

        # rui has followed all his following users
        response = self.rui_client.get(url, {'page': 1})
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], True)

    def _test_friendship_pagination(self, url, page_size, max_page_size):
        response = self.anonymous_client.get(url, {'page': 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)

        response = self.anonymous_client.get(url, {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 2)
        self.assertEqual(response.data['has_next_page'], False)

        response = self.anonymous_client.get(url, {'page': 3})
        self.assertEqual(response.status_code, 404)

        # test user cannot customize page_size exceeds max_page_size
        response = self.anonymous_client.get(url, {'page': 1, 'size': max_page_size + 1})
        self.assertEqual(len(response.data['results']), max_page_size)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)

        # test user cannot customize page size by param size
        response = self.anonymous_client.get(url, {'page': 1, 'size': 2})
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['total_pages'], page_size)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)
