# -*- coding: utf-8 -*-
import os
import time
import unittest
from configparser import ConfigParser

from kb_ad_vina.kb_ad_vinaImpl import kb_ad_vina
from kb_ad_vina.kb_ad_vinaServer import MethodContext
from kb_ad_vina.authclient import KBaseAuth as _KBaseAuth

from installed_clients.WorkspaceClient import Workspace


class kb_ad_vinaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        token = os.environ.get("KB_AUTH_TOKEN", None)
        config_file = os.environ.get("KB_DEPLOYMENT_CONFIG", None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items("kb_ad_vina"):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg["auth-service-url"]
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update(
            {
                "token": token,
                "user_id": user_id,
                "provenance": [
                    {
                        "service": "kb_ad_vina",
                        "method": "please_never_use_it_in_production",
                        "method_params": [],
                    }
                ],
                "authenticated": 1,
            }
        )
        cls.wsURL = cls.cfg["workspace-url"]
        cls.wsClient = Workspace(cls.wsURL)
        cls.serviceImpl = kb_ad_vina(cls.cfg)
        cls.scratch = cls.cfg["scratch"]
        cls.callback_url = os.environ["SDK_CALLBACK_URL"]
        suffix = int(time.time() * 1000)
        cls.wsName = "test_ContigFilter_" + str(suffix)
        ret = cls.wsClient.create_workspace({"workspace": cls.wsName})  # noqa

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "wsName"):
            cls.wsClient.delete_workspace({"workspace": cls.wsName})
            print("Test workspace was deleted")

    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa
    # @unittest.skip("Skip test for debugging")
    def test_your_method(self):
        # Prepare test objects in workspace if needed using
        # self.getWsClient().save_objects({'workspace': self.getWsName(),
        #                                  'objects': []})
        #
        # Run your method by
        # ret = self.getImpl().your_method(self.getContext(), parameters...)
        #
        # Check returned data with
        # self.assertEqual(ret[...], ...) or other unittest methods
        ret = self.serviceImpl.run_kb_ad_vina(
            self.ctx,
            {
                "workspace_name": self.wsName,
                "receptor_ref": "67060/5/2",
                "ligand_refs": ["67060/2/1", "67060/4/1"],
            },
        )
        # next steps:
        # - download report
        # - assert that the report has expected contents
