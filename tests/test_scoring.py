from dragonbench.scoring import score_answer


def test_tf_bind_exact_interval_scores_high():
    card = {
        "task": "DragonTFBind",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "binding_intervals": [
                    {"sequence_id": "seq_001", "start": 30, "end": 49, "strand": "+"}
                ]
            },
        },
    }
    answer = {
        "predictions": [
            {"sequence_id": "seq_001", "start": 30, "end": 49, "strand": "+", "confidence": 0.95}
        ]
    }
    result = score_answer(card, answer)
    assert result.status == "scored"
    assert result.reward > 0.99
    assert result.subscores["interval_f1_at_iou_0_5"] == 1.0


def test_missing_hidden_answer_is_unscored():
    card = {
        "task": "DragonTFBind",
        "hidden_answer": {"status": "needs_source_extraction", "answer": None},
    }
    result = score_answer(card, {"predictions": []})
    assert result.status == "unscored_missing_hidden_answer"
    assert result.reward == 0.0


def test_variant_effect_uses_rank_correlation():
    card = {
        "task": "DragonVariantEffect",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "variant_scores": [
                    {"variant": "A1V", "score": 0.1},
                    {"variant": "A2V", "score": 0.5},
                    {"variant": "A3V", "score": 0.9},
                ]
            },
        },
    }
    answer = {
        "variant_scores": [
            {"variant": "A1V", "predicted_score": 1.0},
            {"variant": "A2V", "predicted_score": 2.0},
            {"variant": "A3V", "predicted_score": 3.0},
        ]
    }
    result = score_answer(card, answer)
    assert result.status == "scored"
    assert result.subscores["spearman_scaled"] > 0.999


def test_intron_parse_scores_exact_introns():
    card = {
        "task": "DragonGeneParseIntrons",
        "hidden_answer": {
            "status": "verified",
            "answer": {"introns": [{"start": 10, "end": 20}, {"start": 40, "end": 55}]},
        },
    }
    result = score_answer(card, {"introns": [{"start": 10, "end": 20}, {"start": 40, "end": 55}]})
    assert result.status == "scored"
    assert result.reward == 1.0


def test_promoter_expression_scores_ranking():
    card = {
        "task": "DragonAnolePromoterExpression",
        "hidden_answer": {
            "status": "verified",
            "answer": {
                "ordered_tissues": ["limb_bud", "skin", "brain"],
                "expression": {"limb_bud": 10.0, "skin": 5.0, "brain": 1.0},
            },
        },
    }
    result = score_answer(card, {"ordered_tissues": ["limb_bud", "skin", "brain"]})
    assert result.status == "scored"
    assert result.reward > 0.999


def test_protein_folding_scores_contacts():
    card = {
        "task": "DragonProteinFolding",
        "hidden_answer": {
            "status": "verified",
            "answer": {"contacts": [{"i": 1, "j": 8}, {"i": 3, "j": 14}]},
        },
    }
    result = score_answer(card, {"contacts": [{"i": 1, "j": 8}, {"i": 3, "j": 14}]})
    assert result.status == "scored"
    assert result.reward == 1.0


def test_rna_folding_scores_dot_bracket():
    card = {
        "task": "DragonRNAFolding",
        "hidden_answer": {
            "status": "verified",
            "answer": {"dot_bracket": "(((...)))", "base_pairs": [{"i": 0, "j": 8}, {"i": 1, "j": 7}, {"i": 2, "j": 6}]},
        },
    }
    result = score_answer(card, {"dot_bracket": "(((...)))"})
    assert result.status == "scored"
    assert result.reward == 1.0


def test_parser_accepts_xml_wrapped_json():
    card = {
        "task": "DragonRNAFolding",
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
        "task": "DragonRNAFolding",
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
        "task": "DragonRNAFolding",
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
        "task": "DragonRNAFolding",
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
        "task": "DragonRNAFolding",
        "hidden_answer": {
            "status": "verified",
            "answer": {"dot_bracket": "(((...)))", "base_pairs": [{"i": 0, "j": 8}, {"i": 1, "j": 7}, {"i": 2, "j": 6}]},
        },
    }
    result = score_answer(card, 'I think the answer is:\n{"dot_bracket": "(((...)))"}')
    assert result.status == "invalid_answer"
    assert result.reward == 0.0
