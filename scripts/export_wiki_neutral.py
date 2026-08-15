"""Neutral EESG Wiki export.

Keeps clinical page text structurally unchanged. The legacy recommendation-callout
converter remains available in export_wiki.py for a possible future editorial phase,
but is explicitly disabled in the production pipeline for now.
"""

import export_wiki


def passthrough(content: str) -> tuple[str, int]:
    return content, 0


if __name__ == "__main__":
    export_wiki.render_recommendation_blocks = passthrough
    export_wiki.export()
