"""
Tests for v24 migration:
  - API_VERSION constant is "v24"
  - GoogleAdsFieldService get_service call includes version=API_VERSION
  - google-ads package is >= 28.0.0
"""
import importlib.metadata
import unittest
from unittest.mock import MagicMock, call, patch


class TestAPIVersionConstant(unittest.TestCase):
    def test_api_version_is_v24(self):
        from tap_google_ads.streams import API_VERSION
        self.assertEqual(API_VERSION, "v24")

    def test_api_version_starts_with_v(self):
        from tap_google_ads.streams import API_VERSION
        self.assertTrue(API_VERSION.startswith("v"), f"Expected 'v<N>' format, got {API_VERSION!r}")

    def test_api_version_exposed_from_streams_module(self):
        import tap_google_ads.streams as streams_mod
        self.assertTrue(hasattr(streams_mod, "API_VERSION"))

    def test_discover_imports_api_version_from_streams(self):
        import tap_google_ads.discover as discover_mod
        from tap_google_ads.streams import API_VERSION
        self.assertEqual(discover_mod.API_VERSION, API_VERSION)


class TestGoogleAdsFieldServiceVersion(unittest.TestCase):
    def _run_get_api_objects(self):
        mock_client = MagicMock()
        mock_gaf = MagicMock()
        mock_gaf.search_google_ads_fields.return_value = iter([])
        mock_client.get_service.return_value = mock_gaf

        with patch("tap_google_ads.discover.create_sdk_client", return_value=mock_client):
            from tap_google_ads.discover import get_api_objects
            get_api_objects({})

        return mock_client

    def test_get_service_called_with_version_keyword(self):
        mock_client = self._run_get_api_objects()
        _, kwargs = mock_client.get_service.call_args
        self.assertIn("version", kwargs, "get_service must be called with version= kwarg")

    def test_get_service_version_matches_api_version(self):
        from tap_google_ads.streams import API_VERSION
        mock_client = self._run_get_api_objects()
        _, kwargs = mock_client.get_service.call_args
        self.assertEqual(kwargs.get("version"), API_VERSION)

    def test_get_service_service_name_is_unchanged(self):
        mock_client = self._run_get_api_objects()
        args, _ = mock_client.get_service.call_args
        self.assertEqual(args[0], "GoogleAdsFieldService")

    def test_get_service_not_called_without_version(self):
        mock_client = self._run_get_api_objects()
        bare_call = call("GoogleAdsFieldService")
        self.assertNotEqual(
            mock_client.get_service.call_args,
            bare_call,
            "get_service must pass version= — bare call without version is the old behavior",
        )

    def test_search_google_ads_fields_is_called(self):
        mock_client = MagicMock()
        mock_gaf = MagicMock()
        mock_gaf.search_google_ads_fields.return_value = iter([])
        mock_client.get_service.return_value = mock_gaf

        with patch("tap_google_ads.discover.create_sdk_client", return_value=mock_client):
            from tap_google_ads.discover import get_api_objects
            get_api_objects({})

        mock_gaf.search_google_ads_fields.assert_called_once()


class TestGoogleAdsPackageVersion(unittest.TestCase):
    def test_package_is_installed(self):
        try:
            importlib.metadata.version("google-ads")
        except importlib.metadata.PackageNotFoundError:
            self.fail("google-ads package is not installed")

    def test_major_version_is_at_least_28(self):
        version_str = importlib.metadata.version("google-ads")
        major = int(version_str.split(".")[0])
        self.assertGreaterEqual(
            major,
            28,
            f"google-ads {version_str} is below the required >=28.0.0",
        )

    def test_setup_py_requires_google_ads_28(self):
        import pathlib, re
        setup_path = pathlib.Path(__file__).parents[2] / "setup.py"
        content = setup_path.read_text()
        match = re.search(r"google-ads>=(\d+)\.[\d.]+,<(\d+)\.[\d.]+", content)
        if not match:
            self.fail("google-ads versioned requirement (>=X,<Y) not found in setup.py")
        self.assertGreaterEqual(int(match.group(1)), 28)


if __name__ == "__main__":
    unittest.main()
