import json
from typing import Any, Callable


def render_anole_gene_parse_prompt(card: dict[str, Any]) -> str:
    sequence = card["question"]["model_input"]["sequence"]
    return f"""Identify every intron in the green anole genomic DNA sequence below.

Coordinate rules:
- Use zero-based, half-open intervals: start is included and end is excluded.
- Coordinates refer directly to the supplied sequence.
- Return introns in ascending genomic order.
- Do not return exons, a spliced sequence, commentary, or confidence values.

Genomic sequence ({len(sequence)} bases):
{sequence}

Required answer format:
- Return a JSON object with exactly one top-level key: "introns".
- "introns" must be a list.
- Each intron item must have exactly two integer fields: "start" and "end".

Return only the JSON object containing your predicted intron coordinates. Do not use Markdown
or add explanatory text."""


def render_anole_promoter_expression_prompt(card: dict[str, Any]) -> str:
    model_input = card["question"]["model_input"]
    sequence = model_input["promoter_sequence"]
    tissues = model_input["candidate_tissues"]
    tissue_json = json.dumps(tissues, ensure_ascii=False, separators=(",", ":"))
    return f"""Predict the relative tissue expression associated with this 2,000-base sequence
upstream of an Anolis CDS start. Rank the supplied candidate tissues from
highest predicted expression to lowest.

Ranking rules:
- Include every candidate tissue exactly once.
- Use the tissue names exactly as supplied.
- Do not add tissues, omit tissues, duplicate tissues, or include expression
  values.

Candidate tissues:
{tissue_json}

Promoter sequence ({len(sequence)} bases):
{sequence}

Required answer format:
{{"tissue_ranking":["highest_tissue","next_tissue","..."]}}

Return only the JSON object containing the complete ranking. Do not use Markdown
or add explanatory text."""


def render_komodo_protein_fold_prompt(card: dict[str, Any]) -> str:
    sequence = card["question"]["model_input"]["protein_sequence"]
    return f"""Generate a complete all-atom monomer structure for the Komodo dragon
amino-acid sequence below. PDB is preferred for this short protein; mmCIF is
also accepted.

Structure rules:
- Model exactly one monomer whose residues correspond one-for-one, in order, to
  the supplied {len(sequence)}-residue sequence.
- Include valid three-dimensional coordinates and standard residue/atom names.
- Include all atoms. At minimum, every residue must contain N, CA, C, and O
  backbone atoms.
- Use one consistent chain and residue numbering.
- Return one structure string under either "pdb" or "mmcif"; do not return a
  coordinate array, prose, Markdown fences, or both formats.

Protein sequence ({len(sequence)} amino acids):
{sequence}

Required answer format:
{{"pdb":"ATOM      1  N   ...\\n...\\nEND"}}

Alternative accepted task answer:
{{"mmcif":"data_model\\n..."}}

Return only one JSON object containing the complete PDB or mmCIF string. Encode
line breaks as JSON newline escapes. Do not use Markdown or add explanatory
text."""


def render_dragon_tf_bind_prompt(card: dict[str, Any]) -> str:
    model_input = card["question"]["model_input"]
    tf_sequence = model_input["tf_sequence"]
    candidates = model_input["dna_candidates"]
    candidate_json = json.dumps(candidates, ensure_ascii=False, indent=2, sort_keys=True)
    return f"""Given the transcription-factor protein sequence and the DNA candidates below,
estimate the probability that each candidate is bound by the transcription
factor.

Prediction rules:
- Return one probability for every supplied candidate ID.
- Use each candidate ID exactly as supplied.
- Every probability must be a number from 0 through 1.
- Do not return binary labels, explanations, motifs, or additional keys.

Transcription-factor protein sequence ({len(tf_sequence)} amino acids):
{tf_sequence}

DNA candidates:
{candidate_json}

Required answer format:
- Return a JSON object with exactly one top-level key: "binding_probabilities".
- "binding_probabilities" must map every supplied candidate ID to one numeric
  probability from 0 through 1.
- Shape only, using placeholders rather than example values:
  {{"binding_probabilities":{{"<candidate_id>":<number_between_0_and_1>}}}}

Return only the JSON object containing all probabilities. Do not use Markdown or
add explanatory text."""


def render_rna_fold_prompt(card: dict[str, Any]) -> str:
    sequence = card["question"]["model_input"]["sequence"]
    return f"""Predict the secondary structure of the RNA sequence below in dot-bracket
notation.

Dot-bracket rules:
- Return exactly one character per RNA nucleotide.
- Use "." for an unpaired nucleotide and matching "(" and ")" characters for
  paired nucleotides.
- Parentheses must be balanced and properly nested.
- Return only the dot-bracket string in the task answer; do not return base-pair
  indices, energies, prose, or Markdown.

RNA sequence ({len(sequence)} nucleotides):
{sequence}

Required answer format:
{{"dot_bracket":"(((...)))..."}}

Return only the JSON object containing a {len(sequence)}-character dot-bracket
string. Do not use Markdown or add explanatory text."""


TASK_PROMPT_RENDERERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "AnoleGeneParse": render_anole_gene_parse_prompt,
    "AnolePromoterExpression": render_anole_promoter_expression_prompt,
    "KomodoProteinFold": render_komodo_protein_fold_prompt,
    "DragonTFBind": render_dragon_tf_bind_prompt,
    "RNAFold": render_rna_fold_prompt,
}


def render_prompt(card: dict[str, Any]) -> str:
    task = card.get("task")
    try:
        renderer = TASK_PROMPT_RENDERERS[task]
    except KeyError as exc:
        raise ValueError(f"unsupported task prompt: {task}") from exc
    return renderer(card)
