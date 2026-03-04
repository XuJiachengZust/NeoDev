# GitNexus Parser: code parsing + Neo4j storage. Self-contained, copy to any Python project.

from gitnexus_parser.config import load_config
from gitnexus_parser.ingestion.pipeline import run_pipeline, PipelineResult

__all__ = ["run_pipeline", "load_config", "PipelineResult"]
