"""Collect real process results and render reproducible evidence without import effects."""

from .record import EvidenceRun, load_manifest
from .render import render_report

__all__ = ["EvidenceRun", "load_manifest", "render_report"]
