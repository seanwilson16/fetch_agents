# 🧬 Boltz2 Biological Structure Prediction Agent

This agent interfaces with the **Boltz-2** API to generate 3D biomolecular structures from natural language prompts. It supports **proteins**, **DNA**, and **RNA**, with optional **ligands** and **constraints**. Input is validated thoroughly before submission to the API.

See full Boltz API documentation and field descriptions here: https://docs.api.nvidia.com/nim/reference/mit-boltz2-infer

Official Boltz GitHub Repo: https://github.com/jwohlwend/boltz

---

## 🔧 Input Overview

| Field              | Required | Description                                                                 |
|-------------------|----------|-----------------------------------------------------------------------------|
| `polymers`        | ✅ Yes   | List of one or more biomolecules (protein, DNA, or RNA; max 12)                    |
| `ligands`         | ❌ No    | List of small molecules to include (CCD or SMILES; max 20)                      |
| `constraints`     | ❌ No    | List of spatial constraints (pocket or bond constraints)                    |
| `output_format`   | ❌ No    | Format of output file (`mmcif` or `pdb`, default: `mmcif`)                  |
| `recycling_steps` | ❌ No    | Iterative refinement steps (default: 3)                                     |
| `sampling_steps`  | ❌ No    | Diffusion sampling steps (default: 50)                                      |
| `diffusion_samples`| ❌ No   | Number of structures to predict (default: 1)                                  |
| `step_scale`      | ❌ No    | Diffusion step scale (default: 1.638)                                       |
| `without_potentials` | ❌ No | Whether to exclude potential energies (default: `false`)                    |
| `concatenate_msas`| ❌ No    | Merge MSAs across polymers (default: `false`)                               |

---

## 🧬 Polymer Schema

Each polymer object must include:

| Field         | Required | Description                                                                 |
|---------------|----------|-----------------------------------------------------------------------------|
| `id`          | ❌ No     | Single letter (A–Z) or 4-character PDB-style ID                             |
| `molecule_type`| ✅ Yes   | One of: `protein`, `dna`, `rna`                                             |
| `sequence`    | ✅ Yes   | String of length 1–4096                                                     |
| `cyclic`      | ❌ No     | Boolean flag (default: false)                                              |
| `msa`         | ❌ No*    | Dict of alignment records (proteins only)                                  |
| `modifications`| ❌ No    | List of chemical modifications (see below)                                 |

> ⚠️ `msa` can only be provided for proteins.

---

### 🔁 MSA Format (for proteins only)

| Field      | Required | Description                          |
|------------|----------|--------------------------------------|
| `alignment`| ✅ Yes   | MSA content string (e.g. `>seq\nAAA`)|
| `format`   | ✅ Yes   | One of: `a3m`, `csv`, `fasta`, `sto` |
| `rank`     | ❌ No     | Integer to define the ordering of alignments (default: -1)                |

> 📌 **MSA general dictionary structure:**
```
{
  "msa": {
    "<database_name>": {
      "<format>": {
        "alignment": "<alignment_string>",
        "format": "<format_string>"
        "rank": -1
      }
    }
  }
}
```
---

### 🧪 Modifications

| Field       | Required | Description                                     |
|-------------|----------|-------------------------------------------------|
| `ccd`       | ✅ Yes   | Chemical Component Dictionary ID (1–3 chars)    |
| `position`  | ✅ Yes   | 1-based index of residue to modify (integer ≥ 1)|

---

## 🧪 Ligands

Each ligand object can contain either:

| Field    | Required | Description                      |
|----------|----------|----------------------------------|
| `ccd`    | ❌ One of| CCD ID (1–3 characters)          |
| `smiles` | ❌ One of| SMILES string representation     |

> One of `ccd` or `smiles` **must** be included.

---

## 🧷 Constraints

### Pocket Constraints

| Field       | Required | Description                                              |
|-------------|----------|----------------------------------------------------------|
| `binder`    | ✅ Yes   | Must match the `id` of a ligand                          |
| `contacts`  | ✅ Yes   | List of `{ id, residue_index }` (id must match a polymer)|

### Bond Constraints

| Field       | Required | Description                                              |
|-------------|----------|----------------------------------------------------------|
| `atoms`     | ✅ Yes   | List of atoms with `id`, `residue_index`, `atom_name`    |

---

## 🧠 Validation Rules

The agent performs strict checks on inputs:

- `polymers` must be provided and each must have valid `sequence` and `molecule_type`.
- `id` values must be either a single uppercase letter or 4-char alphanumeric string.
- `msa` is **only valid** for `protein`; if present for RNA/DNA, it will be rejected.
- Ligands must have either `ccd` or `smiles`.
- Pocket constraint `binder` must match a ligand `id`.
- All constraint `id` values (for atoms/contacts) must match one of the polymer `id`s.
- Chemical modifications require valid `ccd` and `position`.

---

## ✅ Example Prompts

> **1. Simple protein with ligand and pocket constraint**
> Predict the structure of a protein with ID A and the following sequence:
> `MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQV`.
> Include a ligand with CCD `ATP` (ligand ID `L`).
> Add a pocket constraint where ligand `L` binds to residues 5 and 10 on polymer chain `A`.

---

> **2. Protein with MSA and modification**
> Model a protein with ID `A`, molecule type `protein`, and sequence
> `MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQV`.
> Provide an MSA under `sample1` in `fasta` format:
>
> seq1
> MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQV
>
> seq2
> MTEFKLVIVGSGGVGKSAITIQFIQNYFVDEHDPSIEDSYRQQL
>
> seq3
> MTEYKLVIVGTGGVGKSALTIQLIQNYFVDEYDPTIEESFRKQV
>
> Also include a modification at position 10 with CCD `PTR`.

---

> **3. Protein with SMILES ligand and bond constraint; 3 predicted structures**
>Model a protein with sequence MGLSDGEWQLVLNVWGKVEADIPGHGQEVLIR and ID A.
>Add a ligand with ID L1 and SMILES "CC(=O)OC1=CC=CC=C1C(=O)O".
>Include a bond constraint using atoms with names CA and CB, IDs A and A, and residue indices 5 and 8 respectively.
> Please give me three predictions.

---

## 📤 Output

- A list of predicted biological structures
- Each structure has an average confidence score and clickable link for 3D viewing via Mol*
- Validation feedback if any issues are detected

Example output:
> 🔬 Boltz2 predicted the following biological structure from your query:
>
> 🧬 Structure 1 (avg. confidence: 0.46) | 🔗 [Click to view in 3D](https://molstar.org/viewer/?structure-url=https://gist.githubusercontent.com/sjwilsonfetch/119747058813e9499f5e84fe205759a1/raw/b0f2008a5ff979c4744b74ce93520be2343cc08b/structure_9f68e679-efed-4212-a5f9-c3b4e3f7d114.mmcif&structure-url-format=mmcif)

---

## 🚀 Deployment

This agent runs on [AgentVerse](https://agentverse.ai) and accepts structured messages via `StructuredOutputPrompt`.

---

## 👷 Maintainers

Built by **Sean Wilson**

For support or feature requests, contact: `sean.wilson@fetch.ai`

---

### Citations

1. **Passaro, Saro et al. (2025)**
   Passaro, Saro; Corso, Gabriele; Wohlwend, Jeremy; Reveiz, Mateo; Thaler, Stephan; Somnath, Vignesh Ram; Getz, Noah; Portnoi, Tally; Roy, Julien; Stark, Hannes; Kwabi-Addo, David; Beaini, Dominique; Jaakkola, Tommi; Barzilay, Regina. *Boltz-2: Towards Accurate and Efficient Binding Affinity Prediction.* bioRxiv, 2025. [DOI: 10.1101/2025.06.14.659707](https://doi.org/10.1101/2025.06.14.659707)

2. **Wohlwend, Jeremy et al. (2024)**
   Wohlwend, Jeremy; Corso, Gabriele; Passaro, Saro; Getz, Noah; Reveiz, Mateo; Leidal, Ken; Swiderski, Wojtek; Atkinson, Liam; Portnoi, Tally; Chinn, Itamar; Silterra, Jacob; Jaakkola, Tommi; Barzilay, Regina. *Boltz-1: Democratizing Biomolecular Interaction Modeling.* bioRxiv, 2024. [DOI: 10.1101/2024.11.19.624167](https://doi.org/10.1101/2024.11.19.624167)

3. **Mirdita, Milot et al. (2022)**
   Mirdita, Milot; Schütze, Konstantin; Moriwaki, Yoshitaka; Heo, Lim; Ovchinnikov, Sergey; Steinegger, Martin. *ColabFold: making protein folding accessible to all.* Nature Methods, 2022.
