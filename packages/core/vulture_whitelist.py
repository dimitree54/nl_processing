# image_encoding.py - public API consumed by dependent packages
validate_image_format
encode_path_to_base64
encode_cv2_to_base64

# models.py - Pydantic BaseModel fields accessed via instances
source
target

# ports.py - Protocol interface methods and parameter names
ScoredPairProvider
get_word_pairs_with_scores
RemoteProgressSyncPort
export_remote_snapshot
apply_score_delta
event_id

# prompts.py - public API consumed by dependent packages
build_translation_chain
build_bidirectional_translation_chain

# tiered_helpers.py - public API consumed by dependent packages
compute_next_repeat_state
validate_repeat_state_integrity

# tiered_ports.py - Protocol interface methods and parameter names
get_tiered_candidates
export_tiered_snapshot
apply_tiered_result

# test_tiered_ports.py - non-conforming mock classes used for negative isinstance checks
some_other_method