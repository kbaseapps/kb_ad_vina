# -*- coding: utf-8 -*-
#BEGIN_HEADER
import logging
import os

from installed_clients.CompoundSetUtilsClient import CompoundSetUtils
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.ProteinStructureUtilsClient import ProteinStructureUtils
from .utils import ADVinaApp


#END_HEADER


class kb_ad_vina:
    '''
    Module Name:
    kb_ad_vina

    Module Description:
    A KBase module: kb_ad_vina
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.0.1"
    GIT_URL = "git@github.com:kbaseapps/kb_ad_vina.git"
    GIT_COMMIT_HASH = "41bc526b9ac8990a37af0ca23d8d71a4c99e8719"

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.shared_folder = config['scratch']
        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)
        #END_CONSTRUCTOR
        pass


    def run_kb_ad_vina(self, ctx, params):
        """
        This example function accepts any number of parameters and returns results in a KBaseReport
        :param params: instance of mapping from String to unspecified object
        :returns: instance of type "ReportResults" -> structure: parameter
           "report_name" of String, parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_kb_ad_vina

        config = dict(
            callback_url=self.callback_url,
            shared_folder=self.shared_folder,
            clients=dict(
                CompoundSetUtils=CompoundSetUtils,
                DataFileUtil=DataFileUtil,
                KBaseReport=KBaseReport,
                ProteinStructureUtils=ProteinStructureUtils,
            ),
        )
        # Download Reads

        adv = ADVinaApp(ctx, config=config)
        output = adv.do_analysis(params)

        #END run_kb_ad_vina

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_kb_ad_vina return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
