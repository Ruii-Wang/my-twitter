from testing.testcases import TestCase
from rest_framework.test import APIClient
from friendships.models import Friendship

FOLLOW_URL = '/api/friendships/{}/follow/'
UNFOLLOW_URL = '/api/friendships/{}/unfollow/'
FOLLOWERS_URL = '/api/friendships/{}/followers/'
FOLLOWINGS_URL = '/api/friendships/{}/followings/'

class FriendshipApiTests(TestCase):

    def setUp(self):
        # 匿名用户 其创建已经挪到testcase当中
        # self.anonymous_client = APIClient()

        # 登录用户
        self.ming = self.create_user('ming', 'ming@haha.com')
        self.ming_client = APIClient()
        self.ming_client.force_authenticate(self.ming)

        self.rui = self.create_user('rui', 'rui@haha.com')
        self.rui_client = APIClient()
        self.rui_client.force_authenticate(self.rui)

        # create followings and followers for rui
        for i in range(2):
            follower = self.create_user(
                'rui_follower{}'.format(i),
                'rui_follower{}@haha.com'.format(i),
            )
            Friendship.objects.create(from_user=follower, to_user=self.rui)
        for i in range(3):
            following = self.create_user(
                'rui_following{}'.format(i),
                'rui_following{}@haha.com'.format(i),
            )
            Friendship.objects.create(from_user=self.rui, to_user=following)

    def test_follow(self):
        url = FOLLOW_URL.format(self.ming.id)

        # 需要登录才能follow别人
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 403)

        # 要用post来follow
        response = self.rui_client.get(url)
        self.assertEqual(response.status_code, 405)

        # 不能follow自己
        response = self.ming_client.post(url)
        self.assertEqual(response.status_code, 400)

        # follow成功
        response = self.rui_client.post(url)
        self.assertEqual(response.status_code, 201)
        self.assertEqual('created_at' in response.data, True)
        self.assertEqual('user' in response.data, True)
        self.assertEqual(response.data['user']['id'], self.ming.id)
        self.assertEqual(response.data['user']['username'], self.ming.username)

        # 重复follow会报错
        response = self.rui_client.post(url)
        self.assertEqual(response.status_code, 400)

        # 反向关注会创建新的数据
        count = Friendship.objects.count()
        response = self.ming_client.post(FOLLOW_URL.format(self.rui.id))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Friendship.objects.count(), count+1)

        # follow non-exist user
        response = self.rui_client.post(FOLLOW_URL.format(100))
        self.assertEqual(response.status_code, 404)

    def test_unfollow(self):
        url = UNFOLLOW_URL.format(self.ming.id)

        # 需要登录才能unfollow
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 403)

        # 需要采用post
        response = self.rui_client.get(url)
        self.assertEqual(response.status_code, 405)

        # 自己不能unfollow自己
        response = self.ming_client.post(url)
        self.assertEqual(response.status_code, 400)

        # unfollow成功
        Friendship.objects.create(from_user=self.rui, to_user=self.ming)
        count = Friendship.objects.count()
        response = self.rui_client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted'], 1)
        self.assertEqual(Friendship.objects.count(), count-1)

        # 重复unfollow
        count = Friendship.objects.count()
        response = self.rui_client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted'], 0)
        self.assertEqual(Friendship.objects.count(), count)

    def test_following(self):
        url = FOLLOWINGS_URL.format(self.rui.id)

        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 405)

        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['followings']), 3)
        ts0 = response.data['followings'][0]['created_at']
        ts1 = response.data['followings'][1]['created_at']
        ts2 = response.data['followings'][2]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(ts1 > ts2, True)
        self.assertEqual(
            response.data['followings'][0]['user']['username'],
            'rui_following2'
        )
        self.assertEqual(
            response.data['followings'][1]['user']['username'],
            'rui_following1'
        )
        self.assertEqual(
            response.data['followings'][2]['user']['username'],
            'rui_following0'
        )

    def test_follower(self):
        url = FOLLOWERS_URL.format(self.rui.id)

        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 405)

        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['followers']), 2)
        ts0 = response.data['followers'][0]['created_at']
        ts1 = response.data['followers'][1]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(
            response.data['followers'][0]['user']['username'],
            'rui_follower1'
        )
        self.assertEqual(
            response.data['followers'][1]['user']['username'],
            'rui_follower0'
        )