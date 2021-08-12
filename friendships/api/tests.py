from testing.testcases import TestCase
from rest_framework.test import APIClient
from utils.paginations import EndlessPagination
from friendships.api.paginations import FriendshipPagination
from friendships.services import FriendshipService

FOLLOW_URL = '/api/friendships/{}/follow/'
UNFOLLOW_URL = '/api/friendships/{}/unfollow/'
FOLLOWERS_URL = '/api/friendships/{}/followers/'
FOLLOWINGS_URL = '/api/friendships/{}/followings/'

class FriendshipApiTests(TestCase):

    def setUp(self):
        super(FriendshipApiTests, self).setUp()
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
            self.create_friendship(follower, self.ming)
        for i in range(3):
            following = self.create_user(
                'ming_following{}'.format(i),
            )
            self.create_friendship(self.ming, following)

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
        before_count = FriendshipService.get_following_count(self.rui.id)
        response = self.rui_client.post(FOLLOW_URL.format(self.ming.id))
        self.assertEqual(response.status_code, 201)
        after_count = FriendshipService.get_following_count(self.rui.id)
        self.assertEqual(after_count, before_count + 1)

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
        self.create_friendship(self.ming, self.rui)
        before_count = FriendshipService.get_following_count(self.ming.id)
        response = self.ming_client.post(url)
        after_count = FriendshipService.get_following_count(self.ming.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted'], 1)
        self.assertEqual(after_count, before_count-1)

        # 重复unfollow
        before_count = FriendshipService.get_following_count(self.ming.id)
        response = self.ming_client.post(url)
        after_count = FriendshipService.get_following_count(self.ming.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted'], 0)
        self.assertEqual(after_count, before_count)

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
        page_size = EndlessPagination.page_size
        friendships = []
        for i in range(page_size * 2):
            follower = self.create_user('rui_followers{}'.format(i))
            friendship = self.create_friendship(follower, self.rui)
            friendships.append(friendship)
            if follower.id % 2 == 1:
                self.create_friendship(self.ming, follower)
        url = FOLLOWERS_URL.format(self.rui.id)
        self._paginate_until_the_end(url, 2, friendships)

        # anonymous has not followed any users
        response = self.anonymous_client.get(url)
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], False)

        # ming has followed users with odd id
        response = self.ming_client.get(url)
        for result in response.data['results']:
            has_followed = (result['user']['id'] % 2 == 1)
            self.assertEqual(result['has_followed'], has_followed)

    def test_followings_pagination(self):
        page_size = EndlessPagination.page_size
        friendships = []
        for i in range(page_size * 2):
            following = self.create_user('rui__following{}'.format(i))
            friendship = self.create_friendship(self.rui, following)
            friendships.append(friendship)
            if following.id % 2 == 0:
                self.create_friendship(self.ming, following)
        url = FOLLOWINGS_URL.format(self.rui.id)
        self._paginate_until_the_end(url, 2, friendships)
        # anonymous has not followed any users
        response = self.anonymous_client.get(url)
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], False)

        # ming has followed users with even id
        response = self.ming_client.get(url)
        for result in response.data['results']:
            has_followed = (result['user']['id'] % 2 == 0)
            self.assertEqual(result['has_followed'], has_followed)

        # rui has followed all his following users
        response = self.rui_client.get(url)
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], True)

        # test pull new friendships
        last_created_at = friendships[-1].created_at
        response = self.rui_client.get(url, {'created_at__gt': last_created_at})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

        new_friends = [self.create_user('big_v{}'.format(i)) for i in range(3)]
        new_friendships = []
        for friend in new_friends:
            new_friendships.append(self.create_friendship(from_user=self.rui, to_user=friend))
        response = self.rui_client.get(url, {'created_at__gt': last_created_at})
        self.assertEqual(len(response.data['results']), 3)
        for result, friendship in zip(response.data['results'], reversed(new_friendships)):
            self.assertEqual(result['created_at'], friendship.created_at)

    def _paginate_until_the_end(self, url, expect_pages, friendships):
        results, pages = [], 0
        response = self.anonymous_client.get(url)
        results.extend(response.data['results'])
        pages += 1
        while response.data['has_next_page']:
            self.assertEqual(response.status_code, 200)
            last_item = response.data['results'][-1]
            response = self.anonymous_client.get(url, {
                'created_at__lt': last_item['created_at'],
            })
            results.extend(response.data['results'])
            pages += 1
        self.assertEqual(len(results), len(friendships))
        self.assertEqual(pages, expect_pages)
        # friendship is in ascending order, results is in descending order
        for result, friendship in zip(results, friendships[::-1]):
            self.assertEqual(result['created_at'], friendship.created_at)
