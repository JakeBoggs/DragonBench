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
