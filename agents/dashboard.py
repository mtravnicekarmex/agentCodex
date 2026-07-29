"""Read-only status dashboard for the contract pipeline (see ADR-030).

Run with (from the repository root):

    streamlit run agents/dashboard.py

Shows the contract queue and, for each of the three pipeline roles
(architect, reviewer, programmer), what is currently handed off to them —
derived entirely from the existing file-backed state (`contracts/*.md`,
`agents/<name>/INBOX.md`). It does not start, drive, or talk to any
agent; it only reads what `main.py` and the pipeline have already written
to disk. No conversation transcript is persisted anywhere today, so this
shows the last known state, not a live, turn-by-turn feed — see ADR-030
for why that is a deliberate first step, not an oversight.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit executes this file directly (not as part of the `agents`
# package), so the repository root is not on sys.path by default the way
# it is for `main.py` at the root. Add it explicitly before importing
# anything from `agents.*` — same technique project-level test suites use
# for the same reason (see e.g. project/tests/conftest.py in a cloned
# project).
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from agents.agent import WORKSPACE
from agents.contract_workflow import Contract, ContractStore
from agents.pipeline import inbox_text, role_snapshot

ROLES = ("architect", "reviewer", "programmer")


def _contract_line(contract: Contract) -> str:
    return (
        f"**IMPLEMENTATION_CONTRACT_{contract.number:04d}** — {contract.title}\n\n"
        f"Status: `{contract.status}` · handed off to `{contract.handoff_to}`"
    )


def _latest_note_for(contract: Contract) -> str:
    """The most recent substantial text written about this contract —
    whichever of the last review round or the last point note is newest,
    so the panel shows *why* it is currently sitting with this role."""
    if contract.implementation_review_rounds:
        return contract.implementation_review_rounds[-1].get("summary", "")
    if contract.architecture_review_rounds:
        return contract.architecture_review_rounds[-1].get("findings", "")
    notes = [p.programmer_note for p in contract.points if p.programmer_note]
    if notes:
        return notes[-1]
    return contract.purpose or "(no notes yet — freshly created)"


def render_role_column(role: str, contracts: list[Contract], project_root: Path) -> None:
    st.subheader(role.capitalize())
    if not contracts:
        st.caption("Nothing currently handed off here.")
    for contract in contracts:
        with st.container(border=True):
            st.markdown(_contract_line(contract))
            st.text(_latest_note_for(contract))

    inbox = inbox_text(project_root, role)
    with st.expander("Inbox", expanded=False):
        st.text(inbox if inbox else "(empty)")


def main() -> None:
    st.set_page_config(page_title="agentCodex pipeline status", layout="wide")
    st.title("agentCodex — pipeline status")
    st.caption(
        "Read-only view of the contract pipeline, derived from files on "
        "disk. Does not talk to any agent."
    )

    if st.button("Refresh"):
        st.rerun()

    project_root = WORKSPACE
    store = ContractStore(project_root)
    contracts = store.list_contracts()

    st.header("Contract queue")
    if not contracts:
        st.caption("No contracts yet.")
    else:
        st.table(
            {
                "Number": [f"{c.number:04d}" for c in contracts],
                "Title": [c.title for c in contracts],
                "Status": [c.status for c in contracts],
                "Handed off to": [c.handoff_to for c in contracts],
            }
        )

    st.header("Per-role view")
    snapshot = role_snapshot(store)
    columns = st.columns(len(ROLES))
    for column, role in zip(columns, ROLES):
        with column:
            render_role_column(role, snapshot[role], project_root)


main()
