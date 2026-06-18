"""
Single test covering all three v20 -> v21 migration changes:
  1. API_VERSION is "v21"
  2. GoogleAdsFieldService is called with version=API_VERSION
  3. google-ads package is >= 28.0.0
"""
import importlib.metadata
import unittest
from unittest.mock import MagicMock, patch

from tap_google_ads.streams import API_VERSION


class TestV21Migration(unittest.TestCase):

    def test_v21_migration_changes(self):
        # 1. API version constant
        self.assertEqual(API_VERSION, "v21",
            f"API_VERSION must be 'v21', got '{API_VERSION}'")

        # 2. GoogleAdsFieldService get_service call includes version=API_VERSION
        mock_client = MagicMock()
        mock_gaf = MagicMock()
        mock_gaf.search_google_ads_fields.return_value = iter([])
        mock_client.get_service.return_value = mock_gaf

        with patch("tap_google_ads.discover.create_sdk_client", return_value=mock_client):
            from tap_google_ads.discover import get_api_objects
            get_api_objects({})

        mock_client.get_service.assert_called_once_with(
            "GoogleAdsFieldService", version=API_VERSION
        )

        # 3. google-ads library >= 28.0.0
        installed = importlib.metadata.version("google-ads")
        major = int(installed.split(".")[0])
        self.assertGreaterEqual(major, 28,
            f"google-ads {installed} is below required >=28.0.0")


if __name__ == "__main__":
    unittest.main()
