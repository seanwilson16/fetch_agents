from uagents import Model
from typing import List, Dict
from enum import Enum
import httpx
import requests
import logging
import re
import os

BOLTZ_URL = "https://health.api.nvidia.com/v1/biology/mit/boltz2/predict"

API_KEY = os.getenv("NVCF_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing environment variable: NVCF_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Modification(Model):
    ccd: str
    position: int

class MoleculeType(str, Enum):
    DNA = "dna"
    RNA = "rna"
    PROTEIN = "protein"

class ConstraintType(str, Enum):
    POCKET = "pocket"
    BOND = "bond"

class Contact(Model):
    id: str
    residue_index: int

class PocketConstraint(Model):
    constraint_type: ConstraintType = ConstraintType.POCKET
    binder: str
    contacts: List[Contact]

class Atom(Model):
    id: str
    residue_index: int
    atom_name: str

class BondConstraint(Model):
    constraint_type: ConstraintType = ConstraintType.BOND
    atoms: list[Atom]

class Format(str, Enum):
    CSV = "csv"
    A3M = "a3m"
    FASTA = "fasta"
    STO = "sto"

class AlignmentFileRecord(Model):
    alignment: str
    format: Format
    rank: int = -1

class Polymer(Model):
    id: str | None = None
    molecule_type: MoleculeType
    sequence: str
    cyclic: bool = False
    msa: Dict[str, Dict[Format, AlignmentFileRecord]] | None = None
    modifications: List[Modification] | None = None

class Ligand(Model):
    id: str | None = None
    smiles: str | None = None
    ccd: str | None = None

class Boltz2Request(Model):
    polymers: List[Polymer]
    ligands: List[Ligand] | None = None
    constraints: List[PocketConstraint | BondConstraint] | None = None
    recycling_steps: int = 3
    sampling_steps: int = 50
    diffusion_samples: int = 1
    step_scale: float = 1.638
    without_potentials: bool = False
    output_format: str = "mmcif"
    concatenate_msas: bool = False

class Metric(Model):
    plddt: List[float] | None = None
    ptm: float | None = None
    iptm: float | None = None
    pae: List[List[float]] | None = None
    rmsd: float | None = None
    tm_score: float | None = None

class Structure(Model):
    structure: str
    format: str
    name: str | None = None
    source: str | None = None

class Boltz2Response(Model):
    structures: List[Structure]
    metrics: Dict[str, Metric] | None = None
    confidence_scores: List[float]

def validate_request(ctx: Context, request: dict) -> List[str]:
    issues = []
    VALID_PDB_ID = lambda s: re.fullmatch(r"[A-Z]", s) or re.fullmatch(r"[A-Za-z0-9]{4}", s)

    try:
        # Top-level sanity check
        if request.get("title") == "Boltz2Request":
            issues.append("Issue extracting parameters. Please try again.")
            return issues

        if not request or not isinstance(request, dict):
            issues.append("Please provide a valid request.")
            return issues  # No point continuing if this fails

        # Check required top-level field: polymers
        polymers = request.get("polymers")
        if not isinstance(polymers, list) or not polymers:
            issues.append("Please include at least one valid polymer.")
            return issues  # Can't iterate if this fails

        if len(polymers) > 12:
            issues.append(f"You can include a maximum of 12 polymers! You included {len(polymers)}!")
            return issues

        valid_polymer_ids = set()
        for i, polymer in enumerate(polymers):
            prefix = f"Polymer {i+1}"

            if not isinstance(polymer, dict):
                issues.append(f"{prefix} must be an object.")
                continue

            # ID check: 1 letter (A-Z) or 4-char alphanumeric
            pid = polymer.get("id")
            if isinstance(pid, str) and VALID_PDB_ID(pid):
                valid_polymer_ids.add(pid)
            elif pid is not None:
                issues.append(f"{prefix} has invalid 'id'. Must be a single letter A-Z or 4-character alphanumeric string.")


            # Molecule type check
            mol_type = polymer.get("molecule_type")
            if not isinstance(mol_type, str) or mol_type.lower() not in {"dna", "rna", "protein"}:
                issues.append(f"{prefix} has missing or invalid 'molecule_type'. Must be one of: DNA, RNA, or Protein.")

            # Sequence check
            seq = polymer.get("sequence")
            if not isinstance(seq, str) or not (1 <= len(seq) <= 4096):
                issues.append(f"{prefix} has missing or invalid 'sequence'. Must be a string of length 1–4096.")

            msa = polymer.get("msa")
            if msa is not None:
                if mol_type.lower() != "protein":
                    issues.append(f"{prefix} has msa specified, but msa is only allowed for protein molecules.")
                elif not isinstance(msa, dict):
                    issues.append(f"{prefix} msa must be a dictionary.")
                else:
                    for db_key, format_dict in msa.items():
                        if not isinstance(format_dict, dict):
                            issues.append(f"{prefix} msa[{db_key}] must be a dictionary of format -> alignment records.")
                            continue

                        for fmt_key, record in format_dict.items():
                            if fmt_key not in {"csv", "a3m", "fasta", "sto"}:
                                issues.append(f"{prefix} msa[{db_key}] has unsupported format '{fmt_key}'. Must be one of: csv, a3m, fasta, sto.")
                                continue

                            if not isinstance(record, dict):
                                issues.append(f"{prefix} msa[{db_key}][{fmt_key}] must be a dictionary.")
                                continue

                            alignment = record.get("alignment")
                            if not isinstance(alignment, str) or not alignment.strip():
                                issues.append(f"{prefix} msa[{db_key}][{fmt_key}] is missing a valid 'alignment' string.")

                            fmt = record.get("format")
                            if fmt != fmt_key:
                                issues.append(f"{prefix} msa[{db_key}][{fmt_key}] has mismatched 'format'. Expected '{fmt_key}', got '{fmt}'.")

                            rank = record.get("rank")
                            if rank is not None and not isinstance(rank, int):
                                issues.append(f"{prefix} msa[{db_key}][{fmt_key}] has invalid 'rank'. Must be an integer if present.")

            modifications = polymer.get("modifications")
            if modifications is not None:
                for j, mod in enumerate(modifications):
                    ccd = mod.get("ccd")
                    if not isinstance(ccd, str) or not (1 <= len(ccd) <= 3):
                        issues.append(f"{prefix} modification {j+1} has missing or invalid 'ccd'. Must be a 1—3 character string.")
                    pos = mod.get("position")
                    if not isinstance(pos, int) or pos < 1:
                        issues.append(f"{prefix} modification {j+1} has missing or invalid 'position'. Must be an integer index ≥ 1.")

        ligands = request.get("ligands")
        if ligands is not None:
            valid_ligand_ids = set()

            if len(ligands) > 20:
                issues.append(f"You can include a maximum of 20 ligands! You included {len(ligands)}!")
                return issues

            for i, ligand in enumerate(ligands):
                prefix = f"Ligand {i+1}"

                ccd = ligand.get("ccd")
                smiles = ligand.get("smiles")
                ccd_valid = isinstance(ccd, str) and (1 <= len(ccd) <= 3)
                smiles_valid = isinstance(smiles, str)

                if ccd_valid and smiles_valid:
                    issues.append(f"{prefix} cannot have both a 'CCD' and 'SMILES' string. You must provide one or the other.")
                elif not (ccd_valid or smiles_valid):
                    issues.append(f"{prefix} must include either a 'CCD' (1—3 chars) or a 'SMILES' string.")

                lid = ligand.get("id")
                if isinstance(lid, str) and lid.strip():
                    valid_ligand_ids.add(lid)


        constraints = request.get("constraints")
        if constraints is not None:
            pocket_present = any("binder" in constraint or constraint.get("constraint_type") == "pocket" for constraint in constraints)
            if not valid_polymer_ids:
                issues.append("In order to have constraints, at least one polymer must have a valid ID.")
                if pocket_present and not valid_ligand_ids:
                    issues.append("In order to have a pocket constraint, at least one ligand must have a valid ID.")
            else:
                for i, constraint in enumerate(constraints):
                    prefix = f"Constraint {i+1}"
                    constraint_type = constraint.get("constraint_type")

                    if "binder" in constraint or constraint_type == "pocket":
                        binder = constraint.get("binder")
                        if not valid_ligand_ids:
                            issues.append("In order to have a pocket constraint, at least one ligand must have a valid ID.")
                        else:
                            if not isinstance(binder, str) or len(binder.strip()) == 0:
                                issues.append(f"{prefix} (pocket) is missing a valid 'binder' ID. Must match one of the ligand ids: {', '.join(valid_ligand_ids)}.")
                            elif binder not in valid_ligand_ids:
                                issues.append(f"{prefix} (pocket) binder '{binder}' does not match any ligand id. Valid ligand ids: {', '.join(valid_ligand_ids)}.")

                            contacts = constraint.get("contacts")
                            if not isinstance(contacts, list) or not contacts:
                                issues.append(f"{prefix} (pocket) must have a non-empty list of contacts.")
                            else:
                                for j, contact in enumerate(contacts):
                                    cid = f"{prefix} contact {j+1}"
                                    if not isinstance(contact, dict):
                                        issues.append(f"{cid} must be an object.")
                                        continue
                                    pid = contact.get("id")
                                    if not isinstance(pid, str) or not VALID_PDB_ID(pid):
                                        issues.append(f"{cid} has missing or invalid 'id'. Must match the polymer ids: {', '.join(valid_polymer_ids)}.")
                                    elif pid not in valid_polymer_ids:
                                        issues.append(f"{cid} refers to unknown polymer ID '{pid}'. Must match one of: {', '.join(valid_polymer_ids)}.")
                                    resi = contact.get("residue_index")
                                    if not isinstance(resi, int) or resi < 1:
                                        issues.append(f"{cid} has invalid 'residue_index'. Must be an integer index ≥ 1.")

                    elif "atoms" in constraint or constraint_type == "bond":
                        atoms = constraint.get("atoms")
                        if not isinstance(atoms, list) or not atoms:
                            issues.append(f"{prefix} (bond) must have a non-empty list of atoms.")
                        else:
                            for j, atom in enumerate(atoms):
                                aid = f"{prefix} atom {j+1}"
                                if not isinstance(atom, dict):
                                    issues.append(f"{aid} must be an object.")
                                    continue
                                pid = atom.get("id")
                                if not isinstance(pid, str) or not VALID_PDB_ID(pid):
                                    issues.append(f"{aid} has missing or invalid 'id'. Must match the polymer ids: {', '.join(valid_polymer_ids)}.")
                                elif pid not in valid_polymer_ids:
                                    issues.append(f"{aid} refers to unknown polymer id '{pid}'. Must match one of: {', '.join(valid_polymer_ids)}.")
                                resi = atom.get("residue_index")
                                if not isinstance(resi, int) or resi < 1:
                                    issues.append(f"{aid} has missing or invalid 'residue_index'. Must be an integer index ≥ 1.")
                                name = atom.get("atom_name")
                                if not isinstance(name, str) or len(name.strip()) == 0:
                                    issues.append(f"{aid} has missing or invalid 'atom_name'. Must be a non-empty string.")
                    else:
                        issues.append(f"{prefix} must be either a pocket or bond constraint.")

        return issues

    except Exception as e:
        ctx.logger.error(f"Error during validation of request parameters: {e}")
        raise

def clean_ligand(ligand):
    # Remove whichever field is None (either 'ccd' or 'smiles')
    if ligand.get('ccd') is None:
        del ligand['ccd']  # Remove 'ccd' if it's None
    if ligand.get('smiles') is None:
        del ligand['smiles']  # Remove 'smiles' if it's None
    return ligand

async def get_prediction(ctx: Context, request: Boltz2Request) -> Boltz2Response | str:
    """
    Given a properly formatted Boltz2Request, returns the predicted
    model in the form of a Boltz2Response

    Returns an error in string form if API fails
    """
    try:
        ctx.logger.info(f"Looking up results for {request.polymers}")

        payload = request.model_dump()

        ligands = payload.get("ligands")
        if ligands:
            payload["ligands"] = [clean_ligand(ligand) for ligand in ligands]
        ctx.logger.debug(f"Payload: {payload}")

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {API_KEY}"
        }

        ctx.logger.info("Sending async request to NVIDIA Boltz2 API...")
        async with httpx.AsyncClient() as client:
            response = await client.post(BOLTZ_URL, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            ctx.logger.warning(f"Boltz2 API responded with {response.status_code}: {response.text}")
            return f"Boltz2 API error: {response.text}"

        ctx.logger.info("Successfully received Boltz2 prediction response.")
        return Boltz2Response.model_validate(response.json())

    except Exception as e:
        ctx.logger.error(f"Error during Boltz2 prediction: {str(e)}")
        raise
