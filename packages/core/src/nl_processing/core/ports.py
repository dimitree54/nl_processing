"""Public re-export surface for cross-module ports."""

# Progress ports
from nl_processing.core.progress_ports import RemoteProgressSyncPort, RemoteDeletePort

# Detail ports
from nl_processing.core.detail_ports import DetailedWordRecordPort, WordExtractorPort, PayloadValidatorPort

# Tiered ports
from nl_processing.core.tiered_ports import TieredCandidateProviderPort, RemoteTieredSyncPort

__all__ = [
    "RemoteProgressSyncPort",
    "RemoteDeletePort",
    "DetailedWordRecordPort",
    "WordExtractorPort",
    "PayloadValidatorPort",
    "TieredCandidateProviderPort",
    "RemoteTieredSyncPort",
]
