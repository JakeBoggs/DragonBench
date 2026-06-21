from dragonbench.prompts import render_prompt


def card(task, model_input):
    return {
        "id": "DBEVAL-V0-999",
        "task": task,
        "question": {"model_input": model_input},
    }


def assert_direct_json_contract(prompt):
    assert "Return only" in prompt
    assert "JSON object" in prompt
    assert "Do not use Markdown" in prompt
    assert "submit_answer" not in prompt
    assert "artifact" not in prompt
    assert "answer_ref" not in prompt
    assert "sha256" not in prompt
    assert "<answer>" not in prompt
    assert '"hud_transport_constraint":' not in prompt
    assert "compact coordinate array" not in prompt


def assert_no_benchmark_internals(prompt):
    forbidden = [
        "Question ID:",
        "question_id",
        "Scoring:",
        "reward",
        "metric",
        "diagnostic",
        "Levenshtein",
        "Spearman",
        "AUROC",
        "AUPRC",
        "Brier",
        "RMSD",
        "F1",
        "hidden_answer",
        "source_dataset",
        "lineage",
    ]
    for term in forbidden:
        assert term not in prompt


def test_anole_gene_parse_has_custom_prompt():
    prompt = render_prompt(card("AnoleGeneParse", {"sequence": "AACCGGTT"}))
    assert prompt.startswith("Identify every intron")
    assert "zero-based, half-open intervals" in prompt
    assert "AACCGGTT" in prompt
    assert_direct_json_contract(prompt)
    assert_no_benchmark_internals(prompt)


def test_anole_promoter_expression_has_custom_prompt():
    prompt = render_prompt(card(
        "AnolePromoterExpression",
        {
            "promoter_sequence": "ACGT",
            "candidate_tissues": ["brain", "heart", "liver"],
        },
    ))
    assert prompt.startswith("Predict the relative tissue expression")
    assert "Include every candidate tissue exactly once" in prompt
    assert '["brain","heart","liver"]' in prompt
    assert_direct_json_contract(prompt)
    assert_no_benchmark_internals(prompt)


def test_komodo_protein_fold_has_custom_prompt():
    prompt = render_prompt(card("KomodoProteinFold", {"protein_sequence": "ACDE"}))
    assert prompt.startswith("Generate a complete all-atom monomer structure")
    assert "PDB is preferred" in prompt
    assert "N, CA, C, and O" in prompt
    assert "do not return a\n  coordinate array" in prompt
    assert "JSON newline escapes" in prompt
    assert_direct_json_contract(prompt)
    assert_no_benchmark_internals(prompt)


def test_dragon_tf_bind_has_custom_prompt():
    prompt = render_prompt(card(
        "DragonTFBind",
        {
            "tf_sequence": "MKR",
            "dna_candidates": [
                {"id": "seq_1", "sequence": "ACGT"},
                {"id": "seq_2", "sequence": "TGCA"},
            ],
        },
    ))
    assert prompt.startswith("Given the transcription-factor protein sequence")
    assert "one probability for every supplied candidate ID" in prompt
    assert '"seq_1"' in prompt
    assert "<candidate_id>" in prompt
    assert "<number_between_0_and_1>" in prompt
    assert '"binding_probabilities":{"seq_1"' not in prompt
    assert "0.9" not in prompt
    assert "0.81" not in prompt
    assert_direct_json_contract(prompt)
    assert_no_benchmark_internals(prompt)


def test_rna_fold_has_custom_prompt():
    prompt = render_prompt(card("RNAFold", {"sequence": "AUGCAU"}))
    assert prompt.startswith("Predict the secondary structure")
    assert "exactly one character per RNA nucleotide" in prompt
    assert "balanced and properly nested" in prompt
    assert "6-character" in prompt
    assert_direct_json_contract(prompt)
    assert_no_benchmark_internals(prompt)


def test_unknown_task_raises_instead_of_using_generic_prompt():
    try:
        render_prompt(card("UnknownTask", {}))
    except ValueError as exc:
        assert "unsupported task prompt" in str(exc)
    else:
        raise AssertionError("unknown task unexpectedly used a generic prompt")
