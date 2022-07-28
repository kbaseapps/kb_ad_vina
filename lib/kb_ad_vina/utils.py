"""
This ADVinaApp takes a receptor ref and a list of ligand refs and performs
docking using AutoDock Vina for each (receptor, ligand) pair.
"""
import logging
import os
import re
import subprocess
import uuid

from pprint import pformat
from shutil import copyfile

# This is the SFA base package which provides the Core app class.
from base import Core


def encode_upa_filename(upa):
    """Encode a Unique Permanent Address (upa) into a string suitable for a
       path fragment."""
    ws, obj, ver = upa.split("/")
    return f"_w{ws}o{obj}v{ver}_"


def decode_upa_filename(filename):
    """Decode a filename containing an encoded upa and return that upa."""
    pattern = r"_w([0-9]+)o([0-9]+)v([0-9]+)_"
    # This pattern matches all encoded upas, but only return the first one.
    match_first = re.findall(pattern,filename)[0]
    return "/".join(match_first)


def receptor_as_pdbqt(receptor):
    """
    This function expects receptor to be a path to a receptor in pdb format
    whose file extension is .pdb.
    """
    obabel_cmd_receptor = (
        f"obabel -i pdb {receptor} -o pdbqt -O {receptor}.obabel.pdbqt"
    )
    with subprocess.Popen(
        obabel_cmd_receptor,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        proc.communicate()

    out_filename = f"{receptor}qt"
    with subprocess.Popen(
        f"""grep -e "^\\(ATOM\\|TER\\)" {receptor}.obabel.pdbqt \\
            >> {out_filename}
        """,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        proc.communicate()
    return out_filename


def ligand_as_pdbqt(ligand):
    """
    This function expects ligand to be a path to a ligand in sdf format.
    """
    ligand_obabel_cmd = (
        f"obabel -i sdf {ligand} -o pdbqt -O {ligand}.pdbqt -r"
    )
    with subprocess.Popen(
        ligand_obabel_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        proc.communicate()
    return f"{ligand}.pdbqt"

def pdbqt_ligand_as_sdf(ligand_output):
    """
    This function expects ligand to be a path to a ligand in pdbqt format.
    """
    ligand_output_obabel_cmd = (
        f"obabel -i pdbqt {ligand_output} -o sdf -O {ligand_output}.sdf -r"
    )
    with subprocess.Popen(
        ligand_output_obabel_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        proc.communicate()
    return f"{ligand_output}.sdf"


def run_vina(receptor, ligand, working_directory, params):
    print(f"RUNNING VINA FOR RECEPTOR {receptor} AND LIGAND {ligand}")
    print(f"with parameters {pformat(params)}")
    center_x = params.get("center_x", "-7")
    center_y = params.get("center_y", "78")
    center_z = params.get("center_x", "38.6")
    size_x = params.get("size_x", "34")
    size_y = params.get("size_y", "30")
    size_z = params.get("size_z", "22")
    seed = params.get("seed", "0")
    exhaustiveness = params.get("exhaustiveness", "2")
    num_modes = params.get("num_modes", "10")
    energy_range = params.get("energy_range", "10")
    receptor_filename = os.path.split(receptor)[1]
    ligand_filename = os.path.split(ligand)[1]
    output_path = os.path.join(
        working_directory,
        f"r{receptor_filename}-l{ligand_filename}.pdbqt"
    )
    log_path = os.path.join(
        working_directory,
        f"r{receptor_filename}-l{ligand_filename}.log"
    )
    vina_cmd = f"""vina \\
            --receptor {receptor} \\
            --ligand {ligand} \\
            --center_x {center_x} \\
            --center_y {center_y} \\
            --center_z {center_z} \\
            --size_x {size_x} \\
            --size_y {size_y} \\
            --size_z {size_z} \\
            --out {output_path} \\
            --log {log_path} \\
            --seed {seed} \\
            --exhaustiveness {exhaustiveness} \\
            --num_modes {num_modes} \\
            --energy_range {energy_range} \\
        """
    with subprocess.Popen(
        vina_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as proc:
        proc.communicate()
    return output_path, log_path

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
        self.csu  = self.clients.CompoundSetUtils
        self.dfu = self.clients.DataFileUtil
        self.psu  = self.clients.ProteinStructureUtils
        self.report = self.clients.KBaseReport
        # self.shared_folder is defined in the Core App class.

    def do_analysis(self, params: dict):
        """
        This method is where the main computation will occur.
        """
        receptor_ref = params.get("receptor_ref")
        ligand_refs = params.get("ligand_refs")
        ligands_out_suffix = params.get("ligands_output_suffix")
        self.workspace_id = params["workspace_id"]
        # Download the receptor and ligands from KBase.
        resp_receptor_orig = self.download_receptor(receptor_ref)
        resp_ligands_orig = self.download_ligands(ligand_refs)
        # Download the ligands output suffix from KBase ?
        # Convert inputs to PDBQT.
        receptor_filename = self.receptor_as_pdbqt(resp_receptor_orig)
        ligand_filenames = self.ligands_as_pdbqts(resp_ligands_orig)
        # Run AutoDock Vina on inputs.
        output = self.run_vinas(receptor_filename, ligand_filenames, params)
        # Upload the resulting input and output PDBQT files.
        ligand_output_refs=self.upload_ligands(ligands_out_suffix,output)
        # Generate the report.
        return self.generate_report(output, ligand_output_refs,params)

    def download_ligands(self, ligand_refs):
        """
        Download a list of CompoundSet objects
        param: ligands_ref - A list of ligands references/upas
        """
        ligands = []
        for ligand_ref in ligand_refs:
            out = self.csu.compound_set_to_file({
                "compound_set_ref": ligand_ref,
                "output_format": "sdf",
            })
            src = out["file_path"]
            dst_filename = f"{encode_upa_filename(ligand_ref)}.sdf"
            dst = os.path.join(self.shared_folder, dst_filename)
            ligands.append(copyfile(src, dst))
        return ligands

    def download_receptor(self, receptor_ref):
        """
        Download a receptor ModelProteinStructure object
        param: receptor_ref - the receptor reference/upa
        """
        out = self.psu.export_pdb_structures({ "input_ref": receptor_ref })
        out_filename = f"{encode_upa_filename(receptor_ref)}.pdb"
        out_path = os.path.join(self.shared_folder, out_filename)
        self.dfu.shock_to_file({
            "file_path": out_path,
            "shock_id": out["shock_id"],
            "unpack": "uncompress",
        })
        return out_path

    def ligands_as_pdbqts(self, ligands):
        """
        Convert a list of ligand SDF files into PDBQT files
        param: ligands - the local copy of a compound set
        """
        return [ligand_as_pdbqt(ligand) for ligand in ligands]

    def receptor_as_pdbqt(self, receptor):
        """
        Convert a receptor PDB file into a PDBQT file
        param: receptor - the local copy of a receptor objct
        """
        return receptor_as_pdbqt(receptor)

    def run_vinas(self, receptor_filename, ligand_filenames, params):
        """
        Run AutoDock vina for each pair of receptor and ligand.
        param: receptor_filename - the receptor PDBQT filename
        param: ligand_filenames - a list of ligand PDBQT filenames
        """
        return [
            run_vina(
                receptor_filename,
                ligand_filename,
                self.shared_folder,
                params
            )
            for ligand_filename in ligand_filenames
        ]

    def generate_report(self, output, ligand_output_refs, params: dict):
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
            output=output,
        )
        # The KBaseReport configuration dictionary
        config = dict(
            report_name=f"ADVinaApp_{str(uuid.uuid4())}",
            reports_path=reports_path,
            template_variables=template_variables,
            workspace_name=params["workspace_name"],
        )
        return self.create_report_from_template(template_path, config)

    def upload_ligands(self,ligand_suffix, output):
        """
        Upload a list of CompoundSet objects 
        param:output - pdbqt file and the logfile 
        """
        """
        paths=[path for (path,_) in output]

        params = {
            'workspace_id': self.workspace_id,
            'staging_file_path': path,
            'compound_set_name': 'sdf_set',
        }
        """

        output_ligands = []
        for (o_ligand_ref,_) in output:
            out = self.csu.compound_set_from_file({
                "workspace_id": self.workspace_id,
                "staging_file_path": o_ligand_ref,
                "compound_set_name": 'sdf_set',
            })
            src = out["file_path"]
            dst_filename = f"{encode_upa_filename(o_ligand_ref)}.{ligand_suffix}.sdf"
            dst = os.path.join(self.shared_folder, dst_filename)
            output_ligands.append(copyfile(src, dst))
        return output_ligands

