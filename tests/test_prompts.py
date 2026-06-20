from dragonbench.prompts import render_prompt


def base_card(task="KomodoProteinFold"):
    return {
        "id": "DBEVAL-V0-041",
        "task": task,
        "source": {"primary_dataset": "source"},
        "lineage": "reptile_specific",
        "question": {
            "prompt": "Generate a structure.",
            "model_input": {"protein_sequence": "ACDE"},
        },
        "expected_output_schema": {"pdb": "string"},
        "scoring": {"primary": "distance_matrix_rmsd_score"},
    }


def test_protein_prompt_includes_hud_transport_constraint():
    prompt = render_prompt(base_card())
    assert "hud_transport_constraint" in prompt
    assert "under 60000 characters" in prompt
    assert "coordinates" in prompt
    assert "compact coordinate array" in prompt


def test_non_protein_prompt_omits_hud_transport_constraint():
    prompt = render_prompt(base_card(task="RNAFold"))
    assert '"hud_transport_constraint":' not in prompt
    assert "under 60000 characters" not in prompt
