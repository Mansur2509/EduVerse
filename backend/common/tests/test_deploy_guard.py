from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.deploy_guard import validate_deploy_config


class ValidateDeployConfigTests(SimpleTestCase):
    def test_debug_true_allows_any_format(self):
        validate_deploy_config(
            debug=True,
            allowed_hosts=["https://example.com"],
            cors_allowed_origins=["example.com/"],
            csrf_trusted_origins=["example.com"],
        )

    def test_debug_false_clean_values_pass(self):
        validate_deploy_config(
            debug=False,
            allowed_hosts=["eduverse-vvw2.onrender.com", "uni-way-beta.vercel.app"],
            cors_allowed_origins=["https://uni-way-beta.vercel.app"],
            csrf_trusted_origins=["https://uni-way-beta.vercel.app"],
        )

    def test_debug_false_allowed_hosts_with_protocol_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_deploy_config(
                debug=False,
                allowed_hosts=["https://eduverse-vvw2.onrender.com"],
                cors_allowed_origins=["https://uni-way-beta.vercel.app"],
                csrf_trusted_origins=["https://uni-way-beta.vercel.app"],
            )

    def test_debug_false_cors_origin_missing_protocol_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_deploy_config(
                debug=False,
                allowed_hosts=["eduverse-vvw2.onrender.com"],
                cors_allowed_origins=["uni-way-beta.vercel.app"],
                csrf_trusted_origins=["https://uni-way-beta.vercel.app"],
            )

    def test_debug_false_cors_origin_trailing_slash_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_deploy_config(
                debug=False,
                allowed_hosts=["eduverse-vvw2.onrender.com"],
                cors_allowed_origins=["https://uni-way-beta.vercel.app/"],
                csrf_trusted_origins=["https://uni-way-beta.vercel.app"],
            )

    def test_debug_false_csrf_origin_with_path_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_deploy_config(
                debug=False,
                allowed_hosts=["eduverse-vvw2.onrender.com"],
                cors_allowed_origins=["https://uni-way-beta.vercel.app"],
                csrf_trusted_origins=["https://uni-way-beta.vercel.app/callback"],
            )
