"""
This ADVinaApp demonstrates how to use best practices for KBase App
development using the SFA base package.
"""
import logging
import os
import subprocess
import uuid

from collections import Counter
from shutil import copyfile

# This is the SFA base package which provides the Core app class.
from base import Core

MODULE_DIR = "/kb/module"
TEMPLATES_DIR = os.path.join(MODULE_DIR, "lib/templates")


class ADVinaApp(Core):
    def __init__(self, ctx, config, clients_class=None):
        """
        This is required to instantiate the Core App class with its defaults
        and allows you to pass in more clients as needed.
        """
        super().__init__(ctx, config, clients_class)
        # Here we adjust the instance attributes for our convenience.
        self.report = self.clients.KBaseReport
        self.csu  = self.clients.CompoundSetUtils
        self.psu  = self.clients.ProteinStructureUtils
        # self.shared_folder is defined in the Core App class.
        # TODO Add a self.wsid = a conversion of self.wsname

    def do_analysis(self, params: dict):
        """
        This method is where the main computation will occur.
        """
        receptor_ref = params.get("receptor_ref")
        ligand_refs = params.get("ligand_refs")
        # Download the receptor and ligands from KBase.
        resp_receptor_orig = self.download_receptor(receptor_ref)
        resp_ligands_orig = self.download_ligands(ligand_refs)
        # Convert inputs to PDBQT.
        receptor_filename = self.receptor_as_pdbqt(resp_receptor_orig)
        ligand_filenames = self.ligands_as_pdbqts(resp_ligands_orig)
        # Run AutoDock Vina on inputs.
        self.run_vinas(receptor_filename, ligand_filenames, params)
        # Upload the resulting input and output PDBQT files.
        # Generate the report.
        return self.generate_report(params)

    def download_ligands(self, ligands_ref):
        """
        Download a list of CompoundSet objects
        param: ligands_ref - A list of ligands references/upas
        """

    def download_receptor(self, receptor_ref):
        """
        Download a receptor ModelProteinStructure object
        param: receptor_ref - the receptor reference/upa
        """

    def ligands_as_pdbqts(self, ligands):
        """
        Convert a list of ligand SDF files into PDBQT files
        param: ligands - the local copy of a compound set
        """

    def receptor_as_pdbqt(self, receptor):
        """
        Convert a receptor PDB file into a PDBQT file
        param: receptor - the local copy of a receptor objct
        """

    def run_vinas(self, receptor_filename, ligand_filenames, params):
        """
        Run AutoDock vina for each pair of receptor and ligand.
        param: receptor_filename - the receptor PDBQT filename
        param: ligand_filenames - a list of ligand PDBQT filenames
        """

    def generate_report(self, params: dict):
        """
        This method is where to define the variables to pass to the report.
        """
        # This path is required to properly use the template.
        reports_path = os.path.join(self.shared_folder, "reports")
        # Path to the Jinja template. The template can be adjusted to change
        # the report.
        template_path = os.path.join(TEMPLATES_DIR, "report.html")
        # A sample multiplication table to use as output
        table = [[i * j for j in range(10)] for i in range(10)]
        headers = "one two three four five six seven eight nine ten".split(" ")
        # The keys in this dictionary will be available as variables in the
        # Jinja template. With the current configuration of the template
        # engine, HTML output is allowed.
        template_variables = dict(
            headers=headers,
            table=table,
        )
        # The KBaseReport configuration dictionary
        config = dict(
            report_name=f"ADVinaApp_{str(uuid.uuid4())}",
            reports_path=reports_path,
            template_variables=template_variables,
            workspace_name=params["workspace_name"],
        )
        return self.create_report_from_template(template_path, config)
