from friendships.models import Friendship
from friendships.services import FriendshipService
from testing.testcases import TestCase

class FriendshipServiceTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.rui = self.create_user('rui')
        self.ming = self.create_user('ming')

    def test_get_following(self):
        user1 = self.create_user('user1')
        user2 = self.create_user('user2')
        for to_user in [user1, user2, self.ming]:
            Friendship.objects.create(from_user = self.rui, to_user = to_user)

        user_id_set = FriendshipService.get_following_user_id_set(self.rui.id)
        self.assertSetEqual(user_id_set, {user1.id, user2.id, self.ming.id})

        Friendship.objects.filter(from_user = self.rui, to_user = self.ming).delete()
        user_id_set = FriendshipService.get_following_user_id_set(self.rui.id)
        self.assertSetEqual(user_id_set, {user1.id, user2.id})