import unittest
from unittest.mock import patch, mock_open
from config import open_config

class TestConfig(unittest.TestCase):
    @patch('builtins.open', new_callable=mock_open, read_data='key: value')
    def test_open_config_success(self, mock_file):
        expected_config = {'key': 'value'}
        config = open_config()
        self.assertEqual(config, expected_config)

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_open_config_file_not_found(self, mock_file):
        config = open_config()
        self.assertIsNone(config)

if __name__ == '__main__':
    unittest.main()