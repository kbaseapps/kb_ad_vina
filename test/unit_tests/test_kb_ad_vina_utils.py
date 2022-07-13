import logging
import math
import os
import subprocess

import pytest

from kb_ad_vina.utils import ligand_as_pdbqt, receptor_as_pdbqt, run_vina


def clean():
    with subprocess.Popen(
        ["rm *.pdbqt"],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        proc.communicate()


EPSILON = 0.5
MODULE_HOME = (
    "/kb/module" if os.environ.get("KBASE_CONTAINER") == "yes" else "."
)
os.chdir(os.path.join(MODULE_HOME, "test/data"))
affinity = {
    "Structure2D_CID_49846579.sdf": -8.1,
    "Structure2D_CID_139024764.sdf": -7.9,
}
clean()


@pytest.fixture
def ligands():
    return sorted(affinity.keys(), reverse=True)


@pytest.fixture
def receptor():
    return "6wzu.pdb"


def test_01_pdb_to_pdbqt(receptor):
    receptor_converted = receptor_as_pdbqt(receptor)
    with open(receptor_converted) as f:
        lines = f.readlines()
    for line in lines:
        assert line.startswith("ATOM") or line.startswith("TER")


def test_02_sdfs_to_pdbqt(ligands):
    for ligand in ligands:
        ligand_pdbqt = ligand_as_pdbqt(ligand)

        assert ligand_pdbqt == f"{ligand}.pdbqt"

def test_03_vina(receptor, ligands):
    for ligand in ligands:
        receptor_filename = f"{receptor}qt"
        ligand_filename = f"{ligand}.pdbqt"
        log_filename = f"{receptor}-{ligand}.log"
        output, log = run_vina(receptor_filename, ligand_filename, ".", {})
        with subprocess.Popen(
            f"head -n27 {log} | tail -n1 | awk '{{ print $2 }}'",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            stdout, stderr = proc.communicate()
            assert len(stderr) == 0
            assert math.isclose(
                affinity[ligand],
                float(stdout.decode("utf-8", "ignore")[:-1]),
                abs_tol=EPSILON,
            )
