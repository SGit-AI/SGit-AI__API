import sgit_ai_api
from unittest                    import TestCase
from osbot_utils.utils.Files     import parent_folder, file_name
from sgit_ai_api.utils.Version   import version__sgit_ai_api, Version


class test_Version(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.version = Version()

    def test_path_code_root(self):
        assert self.version.path_code_root() == sgit_ai_api.path

    def test_path_version_file(self):
        with self.version as _:
            assert parent_folder(_.path_version_file()) == sgit_ai_api.path
            assert file_name    (_.path_version_file()) == 'version'

    def test_value(self):
        assert self.version.value() == version__sgit_ai_api
        assert str(self.version.value()).startswith('v')
