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


def test_prompt_requires_submit_answer_receipt():
    prompt = render_prompt(base_card())
    assert "calling the submit_answer tool" in prompt
    assert "answer_ref" in prompt
    assert "sha256" in prompt
    assert "Direct answers inside <answer> are invalid" in prompt


def test_non_protein_prompt_uses_same_submission_contract():
    prompt = render_prompt(base_card(task="RNAFold"))
    assert '"hud_transport_constraint":' not in prompt
    assert "under 60000 characters" not in prompt
    assert "calling the submit_answer tool" in prompt
    assert "answer_ref" in prompt
