import unittest

from services import badge_for_verified, calculate_severity, valid_email


class ServiceTests(unittest.TestCase):
    def test_email_validation(self):
        self.assertTrue(valid_email('citizen@example.com'))
        self.assertFalse(valid_email('not-an-email'))

    def test_highway_pothole_more_severe_than_residential_light(self):
        pothole_score, _ = calculate_severity('Road', 'Pothole', 'Highway')
        light_score, _ = calculate_severity('Lighting', 'Broken Streetlight', 'Residential Area')
        self.assertGreater(pothole_score, light_score)

    def test_badges(self):
        self.assertEqual(badge_for_verified(0)['name'], 'New Citizen')
        self.assertEqual(badge_for_verified(10)['name'], 'Road Warrior')


if __name__ == '__main__':
    unittest.main()
