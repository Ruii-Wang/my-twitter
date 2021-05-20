from testing.testcases import TestCase

class CommentModelTests(TestCase):

    def setUp(self):
        self.rui = self.create_user('rui')
        self.tweet = self.create_tweet(self.rui)
        self.comment = self.create_comment(self.rui, self.tweet)

    def test_comment(self):
        self.assertNotEqual(self.comment.__str__(), None)

    def test_like_set(self):
        self.create_like(self.rui, self.comment)
        self.assertEqual(self.comment.like_set.count(), 1)

        self.create_like(self.rui, self.comment)
        self.assertEqual(self.comment.like_set.count(), 1)

        ming = self.create_user('ming')
        self.create_like(ming, self.comment)
        self.assertEqual(self.comment.like_set.count(), 2)