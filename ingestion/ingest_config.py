from dataclasses import dataclass, field

@dataclass
class IngestConfig:
    chunk_size: int = 512
    overlap: int = 64
    include_pdf: bool = False
    exclude_exts: set = field(default_factory=set)
    reset_collection: bool = False
    dry_run: bool = False
    skip_filter: bool = False
    source_priority: list = field(default_factory=lambda: ["internal_data", "output"])
        