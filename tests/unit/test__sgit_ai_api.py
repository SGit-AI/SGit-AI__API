import sgit_ai_api
from unittest                import TestCase
from osbot_utils.utils.Files import folder_exists, file_exists, path_combine


class test__sgit_ai_api(TestCase):

    def test_package_name(self):
        assert sgit_ai_api.package_name == 'sgit_ai_api'

    def test_path(self):
        assert folder_exists(sgit_ai_api.path)

    def test_version_file_exists(self):
        assert file_exists(path_combine(sgit_ai_api.path, 'version'))
