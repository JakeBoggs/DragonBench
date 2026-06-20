from dragonbench.scoring import score_answer


def test_missing_hidden_answer_is_unscored():
    card = {
        "task": "DragonTFBind",
        "hidden_answer": {"status": "needs_source_extraction", "answer": None},
    }
    result = score_answer(card, {"predictions": []})
    assert result.status == "unscored_missing_hidden_answer"
    assert result.reward == 0.0


def test_anole_gene_parse_uses_spliced_sequence_levenshtein():
    sequence = "AAA" + "CCCC" + "GTGGAG" + "TTTT" + "GGG"
    card = {
        "task": "AnoleGeneParse",
        "question": {"model_input": {"sequence": sequence}},
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "introns": [{"start": 7, "end": 13}],
                "spliced_sequence": "AAACCCCTTTTGGG",
            },
        },
    }
    result = score_answer(card, {"introns": [{"start": 7, "end": 13}]})
    assert result.status == "scored"
    assert result.reward == 1.0
    assert result.subscores["spliced_sequence_levenshtein_similarity"] == 1.0


def test_anole_promoter_expression_accepts_tissue_ranking():
    card = {
        "task": "AnolePromoterExpression",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "tissue_ranking": ["heart", "brain", "liver"],
                "expression": {"heart": 10.0, "brain": 5.0, "liver": 1.0},
            },
        },
    }
    result = score_answer(card, {"tissue_ranking": ["heart", "brain", "liver"]})
    assert result.status == "scored"
    assert result.reward > 0.999


def test_protein_folding_scores_coordinates():
    card = {
        "task": "KomodoProteinFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "coordinates": [
                    {"residue_index": 0, "x": 0, "y": 0, "z": 0},
                    {"residue_index": 1, "x": 1, "y": 0, "z": 0},
                    {"residue_index": 2, "x": 1, "y": 1, "z": 0},
                ]
            },
        },
    }
    result = score_answer(card, {
        "coordinates": [
            {"residue_index": 0, "x": 0, "y": 0, "z": 0},
            {"residue_index": 1, "x": 1, "y": 0, "z": 0},
            {"residue_index": 2, "x": 1, "y": 1, "z": 0},
        ]
    })
    assert result.status == "scored"
    assert result.reward == 1.0


def test_komodo_protein_fold_scores_pdb_string():
    card = {
        "task": "KomodoProteinFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "coordinates": [
                    {"residue_index": 0, "x": 0, "y": 0, "z": 0},
                    {"residue_index": 1, "x": 1, "y": 0, "z": 0},
                    {"residue_index": 2, "x": 1, "y": 1, "z": 0},
                ]
            },
        },
    }
    pdb = "\n".join([
        "ATOM      1  N   GLY A   1      -1.000   0.000   0.000  1.00  0.00           N",
        "ATOM      2  CA  GLY A   1       0.000   0.000   0.000  1.00  0.00           C",
        "ATOM      3  C   GLY A   1       0.500   0.000   0.000  1.00  0.00           C",
        "ATOM      4  O   GLY A   1       0.750   0.000   0.000  1.00  0.00           O",
        "ATOM      5  N   GLY A   2       0.000  -1.000   0.000  1.00  0.00           N",
        "ATOM      6  CA  GLY A   2       1.000   0.000   0.000  1.00  0.00           C",
        "ATOM      7  C   GLY A   2       1.500   0.000   0.000  1.00  0.00           C",
        "ATOM      8  O   GLY A   2       1.750   0.000   0.000  1.00  0.00           O",
        "ATOM      9  N   GLY A   3       1.000   0.000  -1.000  1.00  0.00           N",
        "ATOM     10  CA  GLY A   3       1.000   1.000   0.000  1.00  0.00           C",
        "ATOM     11  C   GLY A   3       1.500   1.000   0.000  1.00  0.00           C",
        "ATOM     12  O   GLY A   3       1.750   1.000   0.000  1.00  0.00           O",
        "END",
    ])
    result = score_answer(card, {"pdb": pdb})
    assert result.status == "scored"
    assert result.reward == 1.0
    assert result.subscores["structure_validity"] == 1.0


def test_tf_bind_scores_binding_probabilities():
    card = {
        "task": "DragonTFBind",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "binding_probabilities": {
                    "seq_01": 0.95,
                    "seq_02": 0.75,
                    "seq_03": 0.05,
                    "seq_04": 0.01,
                }
            },
        },
    }
    result = score_answer(card, {"binding_probabilities": {"seq_01": 0.9, "seq_02": 0.7, "seq_03": 0.1, "seq_04": 0.0}})
    assert result.status == "scored"
    assert result.reward > 0.99
    assert result.subscores["auroc"] == 1.0


def test_rnafold_task_name_scores_dot_bracket():
    card = {
        "task": "RNAFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {"dot_bracket": "(((...)))"},
        },
    }
    result = score_answer(card, {"dot_bracket": "(((...)))"})
    assert result.status == "scored"
    assert result.reward == 1.0


def test_parser_accepts_xml_wrapped_json():
    card = {
        "task": "RNAFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {"dot_bracket": "(((...)))", "base_pairs": [{"i": 0, "j": 8}, {"i": 1, "j": 7}, {"i": 2, "j": 6}]},
        },
    }
    answer = '<answer>{"dot_bracket": "(((...)))"}</answer>'
    result = score_answer(card, answer)
    assert result.status == "scored"
    assert result.reward == 1.0


def test_parser_accepts_reasoning_with_final_answer_xml():
    card = {
        "task": "RNAFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {"dot_bracket": "(((...)))", "base_pairs": [{"i": 0, "j": 8}, {"i": 1, "j": 7}, {"i": 2, "j": 6}]},
        },
    }
    answer = 'I think through the sequence first.\n<answer>{"dot_bracket": "(((...)))"}</answer>'
    result = score_answer(card, answer)
    assert result.status == "scored"
    assert result.reward == 1.0


def test_parser_uses_last_answer_block():
    card = {
        "task": "RNAFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {"dot_bracket": "(((...)))", "base_pairs": [{"i": 0, "j": 8}, {"i": 1, "j": 7}, {"i": 2, "j": 6}]},
        },
    }
    answer = 'Reasoning.\n<answer>{"dot_bracket": "........."}</answer>\n<answer>{"dot_bracket": "(((...)))"}</answer>'
    result = score_answer(card, answer)
    assert result.status == "scored"
    assert result.reward == 1.0


def test_parser_rejects_uppercase_answer_tag():
    card = {
        "task": "RNAFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {"dot_bracket": "(((...)))", "base_pairs": [{"i": 0, "j": 8}, {"i": 1, "j": 7}, {"i": 2, "j": 6}]},
        },
    }
    result = score_answer(card, '<Answer>{"dot_bracket": "(((...)))"}</Answer>')
    assert result.status == "invalid_answer"
    assert result.reward == 0.0


def test_parser_rejects_prose_without_final_answer_xml():
    card = {
        "task": "RNAFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {"dot_bracket": "(((...)))", "base_pairs": [{"i": 0, "j": 8}, {"i": 1, "j": 7}, {"i": 2, "j": 6}]},
        },
    }
    result = score_answer(card, 'I think the answer is:\n{"dot_bracket": "(((...)))"}')
    assert result.status == "invalid_answer"
    assert result.reward == 0.0
