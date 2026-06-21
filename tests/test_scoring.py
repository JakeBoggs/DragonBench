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


def test_anole_gene_parse_normalizes_levenshtein_by_removed_intron_length():
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

    result = score_answer(card, {"introns": [{"start": 7, "end": 12}]})

    assert result.status == "scored"
    assert result.reward == 5 / 6
    assert result.info["spliced_sequence_levenshtein_distance"] == 1
    assert result.info["spliced_sequence_normalization_length"] == 6


def test_anole_gene_parse_unspliced_prediction_scores_zero():
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

    result = score_answer(card, {"introns": []})

    assert result.status == "scored"
    assert result.reward == 0.0
    assert result.info["spliced_sequence_levenshtein_distance"] == 6
    assert result.info["spliced_sequence_normalization_length"] == 6


def test_anole_gene_parse_missing_sequence_is_schema_error():
    card = {
        "task": "AnoleGeneParse",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "introns": [{"start": 7, "end": 13}],
                "spliced_sequence": "AAACCCCTTTTGGG",
            },
        },
    }

    try:
        score_answer(card, {"introns": [{"start": 7, "end": 13}]})
    except KeyError as exc:
        assert exc.args[0] == "question"
    else:
        raise AssertionError("missing question unexpectedly produced a score result")


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


def test_promoter_expression_incomplete_ranking_is_penalized():
    tissues = [
        "adrenal_gland",
        "brain",
        "dewlap_skin",
        "embryo",
        "heart",
        "liver",
        "lung",
        "ovary",
        "skeletal_muscle",
    ]
    card = {
        "task": "AnolePromoterExpression",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "tissue_ranking": tissues,
                "expression": {
                    tissue: float(len(tissues) - rank)
                    for rank, tissue in enumerate(tissues)
                },
            },
        },
    }
    result = score_answer(card, {"tissue_ranking": ["adrenal_gland"]})
    assert result.status == "invalid_answer"
    assert result.reward == 0.0
    assert result.subscores["ranking_completeness"] == 1 / 9


def test_promoter_expression_reverse_ranking_scores_zero():
    tissues = [
        "adrenal_gland",
        "brain",
        "dewlap_skin",
        "embryo",
        "heart",
        "liver",
        "lung",
        "ovary",
        "skeletal_muscle",
    ]
    card = {
        "task": "AnolePromoterExpression",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "tissue_ranking": tissues,
                "expression": {
                    tissue: float(len(tissues) - rank)
                    for rank, tissue in enumerate(tissues)
                },
            },
        },
    }
    result = score_answer(card, {"tissue_ranking": list(reversed(tissues))})
    assert result.status == "scored"
    assert result.reward == 0.0


def test_protein_folding_rejects_coordinate_array_answer():
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
    assert result.status == "invalid_answer"
    assert result.reward == 0.0


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


def test_protein_folding_low_coverage_caps_reward():
    card = {
        "task": "KomodoProteinFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "coordinates": [
                    {"residue_index": i, "x": float(i), "y": 0.0, "z": 0.0}
                    for i in range(221)
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
        "ATOM     10  CA  GLY A   3       2.000   0.000   0.000  1.00  0.00           C",
        "ATOM     11  C   GLY A   3       2.500   0.000   0.000  1.00  0.00           C",
        "ATOM     12  O   GLY A   3       2.750   0.000   0.000  1.00  0.00           O",
        "END",
    ])
    result = score_answer(card, {"pdb": pdb})
    assert result.status == "scored"
    assert result.subscores["coordinate_coverage"] == 3 / 221
    assert result.reward < 0.02


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


def test_tf_bind_missing_probability_is_invalid_instead_of_zero_filled():
    card = {
        "task": "DragonTFBind",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "binding_probabilities": {
                    "seq_01": 0.95,
                    "seq_02": 0.05,
                }
            },
        },
    }
    result = score_answer(card, {"binding_probabilities": {"seq_01": 0.9}})
    assert result.status == "invalid_answer"
    assert result.reward == 0.0


def test_rnafold_task_name_scores_dot_bracket():
    card = {
        "task": "RNAFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "dot_bracket": "(((...)))",
                "base_pairs": [{"i": 0, "j": 8}, {"i": 1, "j": 7}, {"i": 2, "j": 6}],
            },
        },
    }
    result = score_answer(card, {"dot_bracket": "(((...)))"})
    assert result.status == "scored"
    assert result.reward == 1.0


def test_rnafold_hidden_base_pairs_are_required():
    card = {
        "task": "RNAFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {"dot_bracket": "(((...)))"},
        },
    }
    result = score_answer(card, {"dot_bracket": "(((...)))"})
    assert result.status == "unscored_invalid_hidden_answer"
    assert result.reward == 0.0


def test_rnafold_length_mismatch_is_invalid_instead_of_partial_credit():
    card = {
        "task": "RNAFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "dot_bracket": "(((...)))",
                "base_pairs": [{"i": 0, "j": 8}, {"i": 1, "j": 7}, {"i": 2, "j": 6}],
            },
        },
    }
    result = score_answer(card, {"dot_bracket": "(((...))))"})
    assert result.status == "invalid_answer"
    assert result.reward == 0.0


def test_parser_accepts_raw_json_string():
    card = {
        "task": "RNAFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {"dot_bracket": "(((...)))", "base_pairs": [{"i": 0, "j": 8}, {"i": 1, "j": 7}, {"i": 2, "j": 6}]},
        },
    }
    answer = '{"dot_bracket": "(((...)))"}'
    result = score_answer(card, answer)
    assert result.status == "scored"
    assert result.reward == 1.0


def test_parser_rejects_xml_wrapper():
    card = {
        "task": "RNAFold",
        "hidden_answer": {
            "status": "verified",
            "answer": {"dot_bracket": "(((...)))", "base_pairs": [{"i": 0, "j": 8}, {"i": 1, "j": 7}, {"i": 2, "j": 6}]},
        },
    }
    answer = '<answer>{"dot_bracket": "(((...)))"}</answer>'
    result = score_answer(card, answer)
    assert result.status == "invalid_answer"
    assert result.reward == 0.0


def test_parser_rejects_prose_around_json():
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
