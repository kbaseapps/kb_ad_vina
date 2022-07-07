import logging
import os
import subprocess

import pytest

from kb_ad_vina.utils import ADVinaApp


def approximatelyEqual(float1, float2, epsilon):
    return abs(float1 - float2) < epsilon


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
    "Structure2D_CID_49846579": -8.1,
    "Structure2D_CID_139024764": -7.9,
}
clean()


@pytest.fixture
def ligands():
    return sorted(affinity.keys(), reverse=True)


@pytest.fixture
def receptor():
    return "6wzu"


def test_01_pdb_to_pdbqt(receptor):
    obabel_cmd_receptor = (
        f"obabel -i pdb {receptor}.pdb -o pdbqt -O {receptor}.obabel.pdbqt"
    )
    with subprocess.Popen(
        obabel_cmd_receptor,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        proc.communicate()

    with subprocess.Popen(
        f"""grep -e "^\\(ATOM\\|TER\\)" {receptor}.obabel.pdbqt \\
            >> {receptor}.obabel.clean.pdbqt
        """,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        proc.communicate()

    with open(f"{receptor}.obabel.clean.pdbqt") as f:
        lines = f.readlines()
    for line in lines:
        assert line.startswith("ATOM") or line.startswith("TER")


def test_02_sdfs_to_pdbqt(ligands):
    for ligand in ligands:
        ligand_obabel_cmd = (
            f"obabel -i sdf {ligand}.sdf -o pdbqt -O {ligand}.obabel.pdbqt -r"
        )
        with subprocess.Popen(
            ligand_obabel_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            proc.communicate()
            ligand_proc = proc

        assert ligand_proc.returncode == 0


def test_03_vina(receptor, ligands):
    for ligand in ligands:
        vina_cmd = f"""vina \\
                --receptor {receptor}.obabel.clean.pdbqt \\
                --ligand {ligand}.obabel.pdbqt \\
                --center_x -7 \\
                --center_y 78 \\
                --center_z 38.6 \\
                --size_x 34 \\
                --size_y 30 \\
                --size_z 22 \\
                --out {receptor}-{ligand}.pdbqt \\
                --log test.log \\
                --seed 0\\
                --exhaustiveness 2 \\
                --num_modes 10 \\
                --energy_range 10 \\
            """
        with subprocess.Popen(
            vina_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ) as proc:
            stdout, stderr = proc.communicate()
            logging.info(stdout.decode("utf-8", "ignore"))
        with subprocess.Popen(
            "head -n27 test.log | tail -n1 | awk '{ print $2 }'",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            stdout, stderr = proc.communicate()
            assert approximatelyEqual(
                affinity[ligand],
                float(stdout.decode("utf-8", "ignore")[:-1]),
                EPSILON,
            )
