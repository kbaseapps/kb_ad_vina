"""
This ADVinaApp takes a receptor ref and a list of ligand refs and performs
docking using AutoDock Vina for each (receptor, ligand) pair.
"""
import os
import re
import subprocess
import textwrap
import uuid

from shutil import copyfile, make_archive

# This is the SFA base package which provides the Core app class.
from base import Core  # type: ignore[import]

upa_filename_pattern = r"_w([0-9]+)o([0-9]+)v([0-9]+)_"


def encode_upa_filename(upa):
    """Encode a Unique Permanent Address (upa) into a string suitable for a
    path fragment."""
    ws, obj, ver = upa.split("/")
    return f"_w{ws}o{obj}v{ver}_"


def decode_upa_filename(filename):
    """Decode a filename containing an encoded upa and return that upa."""
    # This pattern matches all encoded upas, but only return the first one.
    match_first = re.findall(upa_filename_pattern, filename)[0]
    return "/".join(match_first)


def get_affinity_from_vina_log(log):
    """Return the highest affinity value from a vina log file."""
    lines = log.split("\n")
    return float(
        [
            [match for match in re.findall(r"([0-9.-]+)", line)][1]
            for line in lines[26:27]
        ][0]
    )


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
    ligand_obabel_cmd = f"obabel -i sdf {ligand} -o pdbqt -O {ligand}.pdbqt -r"
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
    center_x = params.get("center_x", 0)
    center_y = params.get("center_y", 0)
    center_z = params.get("center_x", 0)
    size_x = params.get("size_x", 30)
    size_y = params.get("size_y", 30)
    size_z = params.get("size_z", 30)
    seed = params.get("seed", 0)
    exhaustiveness = params.get("exhaustiveness", 8)
    num_modes = params.get("num_modes", 9)
    energy_range = params.get("energy_range", 3)
    receptor_filename = os.path.split(receptor)[1]
    ligand_filename = os.path.split(ligand)[1]
    log_filename = f"r{receptor_filename}-l{ligand_filename}.log"
    log_path = os.path.join(working_directory, log_filename)
    output_filename = f"r{receptor_filename}-l{ligand_filename}.pdbqt"
    output_path = os.path.join(working_directory, output_filename)
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
        self.csu = self.clients.CompoundSetUtils
        self.dfu = self.clients.DataFileUtil
        self.psu = self.clients.ProteinStructureUtils
        self.report = self.clients.KBaseReport
        self.ws = config["Workspace"](config["ws_url"], token=ctx["token"])
        # self.shared_folder is defined in the Core App class.
        # a cache for Workspace.get_objects2 results
        self.ws_cache = {}
        self.reports_path = os.path.join(self.shared_folder, "reports")
        self._prepare_report_directory()

    def _prepare_report_directory(self):
        self.ligands_input = "ligands_input"
        self.ligands_input_shared = os.path.join(
            self.reports_path, self.ligands_input
        )
        os.makedirs(
            os.path.join(self.reports_path, self.ligands_input), exist_ok=True
        )
        self.vina_output = "vina_output"
        self.vina_output_shared = os.path.join(
            self.reports_path, self.vina_output
        )
        os.makedirs(
            os.path.join(self.reports_path, self.vina_output), exist_ok=True
        )

    def do_analysis(self, params: dict):
        """
        This method is where the main computation will occur.
        """
        receptor_ref = params.get("receptor_ref")
        ligand_refs = params.get("ligand_refs")
        # ligands_out_suffix = params.get("ligands_output_suffix")
        self.workspace_id = params["workspace_id"]
        # Download the receptor and ligands from KBase.
        resp_receptor_orig = self.download_receptor(receptor_ref)
        resp_ligands_orig = self.download_ligands(ligand_refs)
        # Download the ligands output suffix from KBase ?
        # Convert inputs to PDBQT.
        receptor_path = self.receptor_as_pdbqt(resp_receptor_orig)
        self.receptor_filename = os.path.split(receptor_path)[1]
        ligand_filenames = self.ligands_as_pdbqts(resp_ligands_orig)
        # Run AutoDock Vina on inputs.
        output = self.run_vinas(receptor_path, ligand_filenames, params)
        # Upload the resulting input and output PDBQT files.
        # NOTE: Upload is disabled for now since CompoundSetUtils does not
        # support direct uploads at this time.
        # ligand_output_refs = self.upload_ligands(ligands_out_suffix, output)
        # Generate the report.
        return self.generate_report(output, params)

    def download_ligands(self, ligand_refs):
        """
        Download a list of CompoundSet objects
        param: ligands_ref - A list of ligands references/upas
        """
        ligands = []
        ligand_ref_objs = [{"ref": ligand_ref} for ligand_ref in ligand_refs]
        ligand_objects = self.ws.get_objects2({"objects": ligand_ref_objs})[
            "data"
        ]
        responses = {
            ligand_object["path"][0]: ligand_object["data"]
            for ligand_object in ligand_objects
        }
        self.ws_cache.update(responses)
        for ligand_ref in ligand_refs:
            out = self.csu.compound_set_to_file(
                {
                    "compound_set_ref": ligand_ref,
                    "output_format": "sdf",
                }
            )
            src = out["file_path"]
            dst_filename = f"{encode_upa_filename(ligand_ref)}.sdf"
            dst = os.path.join(self.ligands_input_shared, dst_filename)
            ligands.append(copyfile(src, dst))
        return ligands

    def download_receptor(self, receptor_ref):
        """
        Download a receptor ModelProteinStructure object
        param: receptor_ref - the receptor reference/upa
        """
        out = self.psu.export_pdb_structures({"input_ref": receptor_ref})
        message = textwrap.dedent("""
        Currently ProteinStructureUtils stores handles instead of blobstore ids
        """)
        print(message)
        print(out)
        shock_ids = out["shock_ids"]
        if len(shock_ids) > 1:
            raise Exception("Only one receptor is supported by this app.")
        out_filename = f"{encode_upa_filename(receptor_ref)}.pdb"
        out_path = os.path.join(self.reports_path, out_filename)
        self.dfu.shock_to_file(
            {
                "file_path": out_path,
                "handle_id": shock_ids[0],
                "unpack": "uncompress",
            }
        )
        return out_path

    def generate_report(self, output, params: dict):
        """
        This method is where to define the variables to pass to the report.
        """
        # This path is required to properly use the template.
        reports_path = self.reports_path
        # Path to the Jinja template. The template can be adjusted to change
        # the report.
        template_path = os.path.join(TEMPLATES_DIR, "report.html")
        citation = self.get_vina_citation()
        logs = {
            log: self.process_vina_output(pdbqt, log) for (pdbqt, log) in output
        }
        affinitys = {log: logdata["affinity"] for log, logdata in logs.items()}
        # Create archives of output
        oldpwd = os.getcwd()
        os.chdir(self.ligands_input_shared)
        make_archive(f"{self.ligands_input}", "zip")
        os.chdir(self.vina_output_shared)
        make_archive(f"{self.vina_output}", "zip")
        os.chdir(oldpwd)
        # The keys in this dictionary will be available as variables in the
        # Jinja template. With the current configuration of the template
        # engine, HTML output is allowed.
        template_variables = dict(
            affinitys=affinitys,
            ligands_input=self.ligands_input,
            logs=logs,
            output=output,
            params=params,
            receptor=self.receptor_filename,
            vina_output=self.vina_output,
        )
        # Parameters for create_extended_report
        report_name = f"ADVinaApp_{str(uuid.uuid4())}"
        html_links = [
            {
                "description": "Report",
                "name": "index.html",
                "path": reports_path,
            },
        ]
        report_params = {
            "direct_html_link_index": 0,
            "html_links": html_links,
            "message": citation,
            "report_object_name": report_name,
            "workspace_name": params["workspace_name"],
        }
        # The KBaseReport configuration dictionary
        config = dict(
            report_name=report_name,
            report_params=report_params,
            reports_path=reports_path,
            template_variables=template_variables,
            workspace_name=params["workspace_name"],
        )
        return self.create_report_from_template(template_path, config)

    def get_vina_citation(self):
        cmd = textwrap.dedent(
            """
            vina \\
                --receptor . --ligand . \\
                --center_x 0 --center_y 0 --center_z 0 \\
                --size_x 1 --size_y 1 --size_z 1 | head -n13
            """
        )
        with subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            stdout, stderr = proc.communicate()
        assert len(stderr.decode().split("\n")) == 4
        return stdout.decode()

    def ligands_as_pdbqts(self, ligands):
        """
        Convert a list of ligand SDF files into PDBQT files
        param: ligands - the local copy of a compound set
        """
        return [ligand_as_pdbqt(ligand) for ligand in ligands]

    def process_vina_output(self, pdbqt, log):
        receptor, ligand = [
            "/".join(tup) for tup in re.findall(upa_filename_pattern, log)
        ]
        with open(os.path.join(self.shared_folder, log)) as f:
            log_data = f.read()
        ligand_object = self.ws_cache[ligand]
        pdbqt_input = os.path.join(
            self.ligands_input, f"{encode_upa_filename(ligand)}.sdf.pdbqt"
        )
        log_filename = os.path.split(log)[1]
        pdbqt_filename = os.path.split(pdbqt)[1]
        pdbqt_output = f"{self.vina_output}/{pdbqt_filename}"
        log_path = f"{self.vina_output}/{log_filename}"
        return {
            "affinity": get_affinity_from_vina_log(log_data),
            "ligand_pdbqt_input": pdbqt_input,
            "ligand_pdbqt_output": pdbqt_output,
            "log_path": log_path,
            "name": ligand_object["name"],
            "raw": log_data,
            "receptor_ref": receptor,
            "ligand_ref": ligand,
        }

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
                self.vina_output_shared,
                params,
            )
            for ligand_filename in ligand_filenames
        ]

    def upload_ligands(self, ligand_suffix, output):
        """
        Upload a list of CompoundSet objects
        param:output - pdbqt file and the logfile
        """
        output_ligands = []
        for (o_ligand_ref, _) in output:
            out = self.csu.compound_set_from_file(
                {
                    "workspace_id": self.workspace_id,
                    "staging_file_path": os.path.join("../../../", o_ligand_ref),
                    "compound_set_name": "sdf_set",
                }
            )
            src = out["file_path"]
            dst_filename = (
                f"{encode_upa_filename(o_ligand_ref)}.{ligand_suffix}.sdf"
            )
            dst = os.path.join(self.shared_folder, dst_filename)
            output_ligands.append(copyfile(src, dst))
        return output_ligands
