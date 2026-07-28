from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


ContractStatus = Literal[
    "DRAFT",
    "ARCHITECTURE_CHANGES_REQUESTED",
    "REJECTED",
    "READY_FOR_PROGRAMMER",
    "IN_PROGRESS",
    "READY_FOR_ARCHITECT_REVIEW",
    "CHANGES_REQUESTED",
    "APPROVED",
]

PointStatus = Literal["PENDING", "IMPLEMENTED", "APPROVED", "CHANGES_REQUESTED"]

ArchitectureVerdict = Literal["ACCEPTED", "REJECTED", "CHANGES_REQUESTED"]

CONTRACT_FILE_RE = re.compile(r"^IMPLEMENTATION_CONTRACT_(\d{4})\.md$")
META_RE = re.compile(
    r"<!-- CONTRACT-META\s*(\{.*?\})\s*CONTRACT-META -->",
    re.DOTALL,
)

ALLOWED_MEMORY_TARGETS = (
    re.compile(r"^memory/[A-Za-z0-9_.-]+\.md$"),
    re.compile(r"^agents/[A-Za-z0-9_-]+/(MEMORY|WORKING_STATE)\.md$"),
    re.compile(r"^PRINCIPLES\.md$"),
)


@dataclass
class ContractPoint:
    number: int
    assignment: str
    acceptance_criteria: list[str] = field(default_factory=list)
    programmer_note: str = ""
    programmer_files: list[str] = field(default_factory=list)
    programmer_tests: list[str] = field(default_factory=list)
    architect_review: str = ""
    status: PointStatus = "PENDING"


@dataclass
class Contract:
    number: int
    title: str
    status: ContractStatus
    created_by: str
    assigned_to: str
    handoff_to: str
    created_at: str
    updated_at: str
    points: list[ContractPoint]
    implementer: str = "programmer"
    reviewer: str = "reviewer"
    # Why (human-readable architectural intent) — separate from the What (points).
    purpose: str = ""
    intent: str = ""
    current_state: str = ""
    inputs: str = ""
    outputs: str = ""
    out_of_scope: str = ""
    future_evolution: str = ""
    lessons_learned: str = ""
    # Append-only round history for both review gates. Never overwritten,
    # only appended to — a round represents one verdict at one point in time.
    architecture_review_rounds: list[dict[str, Any]] = field(default_factory=list)
    completion_notes: str = ""
    implementation_review_rounds: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class MemoryUpdate:
    path: str
    text: str


class ContractStore:
    """File-backed contract queue and handoff between agents.

    Pipeline (two review gates, three roles, after the Tr5 Implementation
    Contract pattern: Architect / Architecture Reviewer / Implementation Agent):

        create_contract (architect)  -> DRAFT                (-> reviewer)
        record_architecture_review (reviewer):
            ACCEPTED             -> READY_FOR_PROGRAMMER      (-> implementer)
            CHANGES_REQUESTED    -> ARCHITECTURE_CHANGES_REQUESTED (-> architect)
            REJECTED             -> REJECTED                  (-> architect)
        revise_contract (architect, only from ARCHITECTURE_CHANGES_REQUESTED)
            -> DRAFT                                          (-> reviewer)
        claim (programmer)          -> IN_PROGRESS
        record_programmer_result    -> READY_FOR_ARCHITECT_REVIEW (-> architect)
        record_implementation_review (architect):
            APPROVED (all points) -> APPROVED (-> owner)
            otherwise              -> CHANGES_REQUESTED (-> implementer)
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.contracts_dir = self.project_root / "contracts"
        self.contracts_dir.mkdir(parents=True, exist_ok=True)

    def create_contract(
        self,
        title: str,
        points: list[dict[str, Any]],
        *,
        purpose: str = "",
        intent: str = "",
        current_state: str = "",
        inputs: str = "",
        outputs: str = "",
        out_of_scope: str = "",
        future_evolution: str = "",
        created_by: str = "architect",
        implementer: str = "programmer",
        reviewer: str = "reviewer",
    ) -> Contract:
        if not title.strip():
            raise ValueError("A contract must have a title.")

        number = self.next_number()
        now = _timestamp()
        contract_points = _build_points(points)

        contract = Contract(
            number=number,
            title=title.strip(),
            status="DRAFT",
            created_by=created_by,
            assigned_to=reviewer,
            handoff_to=reviewer,
            created_at=now,
            updated_at=now,
            points=contract_points,
            implementer=implementer,
            reviewer=reviewer,
            purpose=purpose.strip(),
            intent=intent.strip(),
            current_state=current_state.strip(),
            inputs=inputs.strip(),
            outputs=outputs.strip(),
            out_of_scope=out_of_scope.strip(),
            future_evolution=future_evolution.strip(),
        )
        self.save(contract)
        return contract

    def revise_contract(
        self,
        number: int,
        title: str,
        points: list[dict[str, Any]],
        *,
        purpose: str = "",
        intent: str = "",
        current_state: str = "",
        inputs: str = "",
        outputs: str = "",
        out_of_scope: str = "",
        future_evolution: str = "",
    ) -> Contract:
        """Rewrite the requirements of a contract returned by the reviewer.

        Only allowed in ARCHITECTURE_CHANGES_REQUESTED — before a contract is
        accepted, no permanent history exists yet (no implementation, no
        inserted annotations), so rewriting the requirements does not violate
        the append-only rule. The history of past architecture review rounds
        (`architecture_review_rounds`) is never cleared. After revision the
        contract returns to DRAFT and is handed back to the reviewer.
        """
        contract = self.load(number)
        if contract.status != "ARCHITECTURE_CHANGES_REQUESTED":
            raise ValueError(
                f"Contract {number:04d} cannot be edited in status {contract.status}."
            )
        if not title.strip():
            raise ValueError("A contract must have a title.")

        contract.title = title.strip()
        contract.points = _build_points(points)
        contract.purpose = purpose.strip()
        contract.intent = intent.strip()
        contract.current_state = current_state.strip()
        contract.inputs = inputs.strip()
        contract.outputs = outputs.strip()
        contract.out_of_scope = out_of_scope.strip()
        contract.future_evolution = future_evolution.strip()
        contract.status = "DRAFT"
        contract.assigned_to = contract.reviewer
        contract.handoff_to = contract.reviewer
        self.save(contract)
        return contract

    def next_number(self) -> int:
        numbers = []
        for path in self.contracts_dir.glob("IMPLEMENTATION_CONTRACT_*.md"):
            match = CONTRACT_FILE_RE.match(path.name)
            if match:
                numbers.append(int(match.group(1)))
        return max(numbers, default=0) + 1

    def path_for(self, number: int) -> Path:
        return self.contracts_dir / f"IMPLEMENTATION_CONTRACT_{number:04d}.md"

    def save(self, contract: Contract) -> Path:
        contract.updated_at = _timestamp()
        path = self.path_for(contract.number)
        path.write_text(render_contract(contract), encoding="utf-8")
        return path

    def load(self, number: int) -> Contract:
        path = self.path_for(number)
        if not path.is_file():
            raise FileNotFoundError(f"Contract does not exist: {path}")
        return parse_contract(path.read_text(encoding="utf-8"))

    def list_contracts(
        self,
        *,
        assigned_to: str | None = None,
        statuses: set[str] | None = None,
    ) -> list[Contract]:
        contracts: list[Contract] = []
        for path in sorted(self.contracts_dir.glob("IMPLEMENTATION_CONTRACT_*.md")):
            match = CONTRACT_FILE_RE.match(path.name)
            if not match:
                continue
            contract = self.load(int(match.group(1)))
            if assigned_to and contract.handoff_to != assigned_to:
                continue
            if statuses and contract.status not in statuses:
                continue
            contracts.append(contract)
        return contracts

    def next_for_architecture_review(self) -> Contract | None:
        contracts = self.list_contracts(
            assigned_to="reviewer",
            statuses={"DRAFT"},
        )
        return contracts[0] if contracts else None

    def next_for_revision(self) -> Contract | None:
        contracts = self.list_contracts(
            assigned_to="architect",
            statuses={"ARCHITECTURE_CHANGES_REQUESTED"},
        )
        return contracts[0] if contracts else None

    def next_for_programmer(self) -> Contract | None:
        contracts = self.list_contracts(
            assigned_to="programmer",
            statuses={"READY_FOR_PROGRAMMER", "CHANGES_REQUESTED"},
        )
        return contracts[0] if contracts else None

    def next_for_implementation_review(self) -> Contract | None:
        contracts = self.list_contracts(
            assigned_to="architect",
            statuses={"READY_FOR_ARCHITECT_REVIEW"},
        )
        return contracts[0] if contracts else None

    def record_architecture_review(
        self,
        number: int,
        *,
        verdict: ArchitectureVerdict | str,
        findings: str,
        memory_updates: list[MemoryUpdate] | None = None,
        from_agent: str = "reviewer",
    ) -> Contract:
        contract = self.load(number)
        if contract.status != "DRAFT":
            raise ValueError(
                f"Architecture review can only be recorded in status DRAFT, "
                f"currently {contract.status}."
            )
        verdict_upper = str(verdict).upper()
        if verdict_upper not in {"ACCEPTED", "REJECTED", "CHANGES_REQUESTED"}:
            raise ValueError(f"Invalid architecture review verdict: {verdict!r}.")
        findings_text = findings.strip()
        if not findings_text:
            raise ValueError("Architecture review must include findings.")

        round_number = len(contract.architecture_review_rounds) + 1
        contract.architecture_review_rounds.append(
            {
                "round": round_number,
                "date": _timestamp(),
                "verdict": verdict_upper,
                "findings": findings_text,
            }
        )

        if verdict_upper == "ACCEPTED":
            contract.status = "READY_FOR_PROGRAMMER"
            contract.assigned_to = contract.implementer
            contract.handoff_to = contract.implementer
            event = "Contract passed architecture review and is ready for implementation."
        elif verdict_upper == "CHANGES_REQUESTED":
            contract.status = "ARCHITECTURE_CHANGES_REQUESTED"
            contract.assigned_to = contract.created_by
            contract.handoff_to = contract.created_by
            event = "Architecture review requires the contract to be revised (see revise_contract)."
        else:
            contract.status = "REJECTED"
            contract.assigned_to = contract.created_by
            contract.handoff_to = contract.created_by
            event = "Contract was rejected in architecture review."

        self.save(contract)

        for update in memory_updates or []:
            self.append_memory(update, source=f"IMPLEMENTATION_CONTRACT_{number:04d}")

        self.notify(
            to_agent=contract.handoff_to,
            from_agent=from_agent,
            contract=contract,
            event=event,
        )
        return contract

    def claim(self, number: int, *, agent: str = "programmer") -> Contract:
        contract = self.load(number)
        if contract.handoff_to != agent:
            raise ValueError(
                f"Contract {number:04d} is handed off to agent {contract.handoff_to!r}, "
                f"not {agent!r}."
            )
        if contract.status not in {"READY_FOR_PROGRAMMER", "CHANGES_REQUESTED"}:
            raise ValueError(
                f"Contract {number:04d} cannot be claimed in status {contract.status}."
            )
        contract.status = "IN_PROGRESS"
        contract.assigned_to = agent
        contract.handoff_to = agent
        self.save(contract)
        return contract

    def record_programmer_result(
        self,
        number: int,
        *,
        summary: str,
        notes: list[dict[str, Any]],
        tests: list[str] | None = None,
        from_agent: str = "programmer",
        to_agent: str = "architect",
    ) -> Contract:
        contract = self.load(number)
        if contract.status != "IN_PROGRESS":
            raise ValueError(
                f"Programmer output can only be recorded in status IN_PROGRESS, "
                f"currently {contract.status}."
            )

        by_number = {int(item["point"]): item for item in notes}
        missing = [point.number for point in contract.points if point.number not in by_number]
        if missing:
            raise ValueError(
                "The programmer must provide a note for every point. Missing points: "
                + ", ".join(map(str, missing))
            )

        global_tests = [str(item).strip() for item in (tests or []) if str(item).strip()]
        for point in contract.points:
            raw = by_number[point.number]
            note = str(raw.get("note", "")).strip()
            if not note:
                raise ValueError(f"Programmer note for point {point.number} is empty.")
            point.programmer_note = note
            point.programmer_files = [
                str(item).strip() for item in raw.get("files", []) if str(item).strip()
            ]
            point.programmer_tests = [
                str(item).strip() for item in raw.get("tests", []) if str(item).strip()
            ] or global_tests
            point.status = "IMPLEMENTED"

        contract.completion_notes = summary.strip()
        contract.status = "READY_FOR_ARCHITECT_REVIEW"
        contract.assigned_to = to_agent
        contract.handoff_to = to_agent
        self.save(contract)
        self.notify(
            to_agent=to_agent,
            from_agent=from_agent,
            contract=contract,
            event="Implementation is done and awaiting implementation review.",
        )
        return contract

    def record_implementation_review(
        self,
        number: int,
        *,
        approved: bool,
        summary: str,
        reviews: list[dict[str, Any]],
        memory_updates: list[MemoryUpdate] | None = None,
        from_agent: str = "architect",
        to_agent: str | None = None,
    ) -> Contract:
        contract = self.load(number)
        if contract.status != "READY_FOR_ARCHITECT_REVIEW":
            raise ValueError(
                f"Implementation review can only be recorded in status "
                f"READY_FOR_ARCHITECT_REVIEW, currently {contract.status}."
            )
        to_agent = to_agent or contract.implementer

        by_number = {int(item["point"]): item for item in reviews}
        missing = [point.number for point in contract.points if point.number not in by_number]
        if missing:
            raise ValueError(
                "The architect must provide a review for every point. Missing points: "
                + ", ".join(map(str, missing))
            )

        any_changes = False
        for point in contract.points:
            raw = by_number[point.number]
            review = str(raw.get("review", "")).strip()
            status = str(raw.get("status", "")).upper()
            if status not in {"APPROVED", "CHANGES_REQUESTED"}:
                raise ValueError(
                    f"Invalid review status for point {point.number}: {status!r}."
                )
            if not review:
                raise ValueError(f"Review for point {point.number} is empty.")
            point.architect_review = review
            point.status = status  # type: ignore[assignment]
            any_changes = any_changes or status == "CHANGES_REQUESTED"

        effective_approved = approved and not any_changes
        summary_text = summary.strip()
        round_number = len(contract.implementation_review_rounds) + 1
        contract.implementation_review_rounds.append(
            {
                "round": round_number,
                "date": _timestamp(),
                "verdict": "APPROVED" if effective_approved else "CHANGES_REQUESTED",
                "summary": summary_text,
                "reviews": [
                    {"point": point.number, "status": point.status, "review": point.architect_review}
                    for point in contract.points
                ],
            }
        )
        contract.status = "APPROVED" if effective_approved else "CHANGES_REQUESTED"
        contract.assigned_to = "owner" if effective_approved else to_agent
        contract.handoff_to = "owner" if effective_approved else to_agent
        self.save(contract)

        for update in memory_updates or []:
            self.append_memory(update, source=f"IMPLEMENTATION_CONTRACT_{number:04d}")

        self.notify(
            to_agent=contract.handoff_to,
            from_agent=from_agent,
            contract=contract,
            event=(
                "Contract was approved."
                if effective_approved
                else "Implementation review requires further changes."
            ),
        )
        return contract

    def append_memory(self, update: MemoryUpdate, *, source: str) -> Path:
        relative = update.path.replace("\\", "/").strip("/")
        if not any(pattern.fullmatch(relative) for pattern in ALLOWED_MEMORY_TARGETS):
            raise ValueError(
                f"Disallowed memory target {update.path!r}. "
                "Only memory/*.md, agents/*/(MEMORY|WORKING_STATE).md, and "
                "PRINCIPLES.md are allowed."
            )
        text = update.text.strip()
        if not text:
            raise ValueError("A memory entry must not be empty.")

        path = (self.project_root / relative).resolve()
        if self.project_root not in path.parents:
            raise ValueError("Memory target is outside the project.")
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8").rstrip() if path.exists() else ""
        entry = (
            f"## {_timestamp()} — {source}\n\n"
            f"{text}\n"
        )
        path.write_text(
            (existing + "\n\n" + entry).lstrip(),
            encoding="utf-8",
        )
        return path

    def notify(
        self,
        *,
        to_agent: str,
        from_agent: str,
        contract: Contract,
        event: str,
    ) -> Path:
        if to_agent == "owner":
            path = self.contracts_dir / "OWNER_INBOX.md"
        else:
            path = self.project_root / "agents" / to_agent / "INBOX.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8").rstrip() if path.exists() else (
            f"# Inbox: {to_agent}\n"
        )
        relative_contract = self.path_for(contract.number).relative_to(self.project_root)
        entry = (
            f"\n\n## {_timestamp()} — IMPLEMENTATION_CONTRACT_{contract.number:04d}\n\n"
            f"- From: `{from_agent}`\n"
            f"- Status: `{contract.status}`\n"
            f"- File: `{relative_contract.as_posix()}`\n"
            f"- Message: {event}\n"
        )
        path.write_text(existing + entry, encoding="utf-8")
        return path


def _build_points(points: list[dict[str, Any]]) -> list[ContractPoint]:
    if not points:
        raise ValueError("A contract must contain at least one point.")
    contract_points: list[ContractPoint] = []
    for index, raw in enumerate(points, start=1):
        assignment = str(raw.get("assignment") or raw.get("description") or "").strip()
        if not assignment:
            raise ValueError(f"Point {index} has no assignment.")
        criteria = raw.get("acceptance_criteria", [])
        if not isinstance(criteria, list):
            raise ValueError(f"acceptance_criteria for point {index} must be a list.")
        contract_points.append(
            ContractPoint(
                number=index,
                assignment=assignment,
                acceptance_criteria=[str(item).strip() for item in criteria if str(item).strip()],
            )
        )
    return contract_points


def render_contract(contract: Contract) -> str:
    meta = json.dumps(asdict(contract), ensure_ascii=False, indent=2)
    lines: list[str] = [
        f"# IMPLEMENTATION_CONTRACT_{contract.number:04d}",
        "",
        f"Status: {contract.status}",
        "",
        "---",
        "",
        "# Workflow",
        "",
        f"- Created by: `{contract.created_by}`",
        f"- Reviewer (architecture review): `{contract.reviewer}`",
        f"- Implementer: `{contract.implementer}`",
        f"- Currently with: `{contract.assigned_to}`",
        f"- Handed off to: `{contract.handoff_to}`",
        f"- Created at: `{contract.created_at}`",
        f"- Updated at: `{contract.updated_at}`",
        "",
        "---",
        "",
        "# Title",
        "",
        contract.title,
        "",
        "---",
        "",
        "# Purpose",
        "",
        contract.purpose or "_Not filled in._",
        "",
        "---",
        "",
        "# Intent",
        "",
        contract.intent or "_Not filled in._",
        "",
        "---",
        "",
        "# Current State",
        "",
        contract.current_state or "_Not filled in._",
        "",
        "---",
        "",
        "# Inputs",
        "",
        contract.inputs or "_Not filled in._",
        "",
        "---",
        "",
        "# Outputs",
        "",
        contract.outputs or "_Not filled in._",
        "",
        "---",
        "",
        "# Functional Requirements",
        "",
    ]

    for point in contract.points:
        lines.extend(
            [
                f"## Point {point.number}",
                "",
                f"SHALL: {point.assignment}",
                "",
                "Acceptance criteria:",
            ]
        )
        if point.acceptance_criteria:
            lines.extend(f"- {item}" for item in point.acceptance_criteria)
        else:
            lines.append("- Not explicitly stated; the result must match the point's assignment.")

        lines.extend(
            [
                "",
                f"> Status: {point.status}",
                "",
                "Programmer note:",
                "",
                point.programmer_note or "_Awaiting implementation._",
                "",
            ]
        )
        if point.programmer_files:
            lines.append("Files touched:")
            lines.extend(f"- `{item}`" for item in point.programmer_files)
            lines.append("")
        if point.programmer_tests:
            lines.append("Tests:")
            lines.extend(f"- {item}" for item in point.programmer_tests)
            lines.append("")
        lines.extend(
            [
                "Architect's implementation review for this point:",
                "",
                point.architect_review or "_Awaiting review._",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            "# Out of Scope",
            "",
            contract.out_of_scope or "_Not filled in._",
            "",
            "---",
            "",
            "# Acceptance Criteria",
            "",
            "Acceptance criteria are listed per point in the Functional "
            "Requirements section.",
            "",
            "---",
            "",
            "# Architecture Review",
            "",
        ]
    )
    if contract.architecture_review_rounds:
        for round_data in contract.architecture_review_rounds:
            lines.extend(
                [
                    f"### Round {round_data['round']} — {round_data['date']} — "
                    f"Verdict: {round_data['verdict']}",
                    "",
                    round_data["findings"],
                    "",
                ]
            )
    else:
        lines.extend(["_Awaiting architecture review._", ""])

    lines.extend(
        [
            "---",
            "",
            "# Future Evolution",
            "",
            contract.future_evolution or "_Not filled in._",
            "",
            "---",
            "",
            "# Completion Notes",
            "",
            contract.completion_notes or "_Awaiting implementation._",
            "",
            "---",
            "",
            "# Implementation Review",
            "",
        ]
    )
    if contract.implementation_review_rounds:
        for round_data in contract.implementation_review_rounds:
            lines.extend(
                [
                    f"### Round {round_data['round']} — {round_data['date']} — "
                    f"Verdict: {round_data['verdict']}",
                    "",
                    round_data["summary"],
                    "",
                ]
            )
    else:
        lines.extend(["_Awaiting implementation review._", ""])

    lines.extend(
        [
            "---",
            "",
            "# Lessons Learned",
            "",
            contract.lessons_learned or "_Not filled in._",
            "",
            "---",
            "",
            "<!-- CONTRACT-META",
            meta,
            "CONTRACT-META -->",
            "",
        ]
    )
    return "\n".join(lines)


def parse_contract(content: str) -> Contract:
    match = META_RE.search(content)
    if not match:
        raise ValueError("File does not contain CONTRACT-META.")
    data = json.loads(match.group(1))
    data["points"] = [ContractPoint(**item) for item in data["points"]]
    return Contract(**data)


def parse_json_response(text: str) -> dict[str, Any]:
    """Parse JSON from a plain response or from a ```json ... ``` block."""
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    candidate = fenced.group(1) if fenced else stripped
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise ValueError(
            "The agent did not return valid JSON. The response was not written to the contract."
        ) from error
    if not isinstance(value, dict):
        raise ValueError("The root of the agent's response must be a JSON object.")
    return value


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
