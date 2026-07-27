from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


ContractStatus = Literal[
    "READY_FOR_PROGRAMMER",
    "IN_PROGRESS",
    "READY_FOR_ARCHITECT_REVIEW",
    "CHANGES_REQUESTED",
    "APPROVED",
]

PointStatus = Literal["PENDING", "IMPLEMENTED", "APPROVED", "CHANGES_REQUESTED"]

CONTRACT_FILE_RE = re.compile(r"^CONTRACT - (\d{4})\.md$")
META_RE = re.compile(
    r"<!-- CONTRACT-META\s*(\{.*?\})\s*CONTRACT-META -->",
    re.DOTALL,
)

ALLOWED_MEMORY_TARGETS = (
    re.compile(r"^memory/[A-Za-z0-9_.-]+\.md$"),
    re.compile(r"^agents/[A-Za-z0-9_-]+/(MEMORY|WORKING_STATE)\.md$"),
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
    programmer_summary: str = ""
    architect_summary: str = ""


@dataclass(frozen=True)
class MemoryUpdate:
    path: str
    text: str


class ContractStore:
    """Souborová fronta kontraktů a předání mezi agenty."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.contracts_dir = self.project_root / "contracts"
        self.contracts_dir.mkdir(parents=True, exist_ok=True)

    def create_contract(
        self,
        title: str,
        points: list[dict[str, Any]],
        *,
        created_by: str = "architect",
        assigned_to: str = "programmer",
    ) -> Contract:
        if not title.strip():
            raise ValueError("Kontrakt musí mít název.")
        if not points:
            raise ValueError("Kontrakt musí obsahovat alespoň jeden bod.")

        number = self.next_number()
        now = _timestamp()
        contract_points: list[ContractPoint] = []

        for index, raw in enumerate(points, start=1):
            assignment = str(raw.get("assignment") or raw.get("description") or "").strip()
            if not assignment:
                raise ValueError(f"Bod {index} nemá zadání.")
            criteria = raw.get("acceptance_criteria", [])
            if not isinstance(criteria, list):
                raise ValueError(f"acceptance_criteria bodu {index} musí být seznam.")
            contract_points.append(
                ContractPoint(
                    number=index,
                    assignment=assignment,
                    acceptance_criteria=[str(item).strip() for item in criteria if str(item).strip()],
                )
            )

        contract = Contract(
            number=number,
            title=title.strip(),
            status="READY_FOR_PROGRAMMER",
            created_by=created_by,
            assigned_to=assigned_to,
            handoff_to=assigned_to,
            created_at=now,
            updated_at=now,
            points=contract_points,
        )
        self.save(contract)
        self.notify(
            to_agent=assigned_to,
            from_agent=created_by,
            contract=contract,
            event="Kontrakt je připraven k implementaci.",
        )
        return contract

    def next_number(self) -> int:
        numbers = []
        for path in self.contracts_dir.glob("CONTRACT - *.md"):
            match = CONTRACT_FILE_RE.match(path.name)
            if match:
                numbers.append(int(match.group(1)))
        return max(numbers, default=0) + 1

    def path_for(self, number: int) -> Path:
        return self.contracts_dir / f"CONTRACT - {number:04d}.md"

    def save(self, contract: Contract) -> Path:
        contract.updated_at = _timestamp()
        path = self.path_for(contract.number)
        path.write_text(render_contract(contract), encoding="utf-8")
        return path

    def load(self, number: int) -> Contract:
        path = self.path_for(number)
        if not path.is_file():
            raise FileNotFoundError(f"Kontrakt neexistuje: {path}")
        return parse_contract(path.read_text(encoding="utf-8"))

    def list_contracts(
        self,
        *,
        assigned_to: str | None = None,
        statuses: set[str] | None = None,
    ) -> list[Contract]:
        contracts: list[Contract] = []
        for path in sorted(self.contracts_dir.glob("CONTRACT - *.md")):
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

    def next_for_programmer(self) -> Contract | None:
        contracts = self.list_contracts(
            assigned_to="programmer",
            statuses={"READY_FOR_PROGRAMMER", "CHANGES_REQUESTED"},
        )
        return contracts[0] if contracts else None

    def next_for_architect_review(self) -> Contract | None:
        contracts = self.list_contracts(
            assigned_to="architect",
            statuses={"READY_FOR_ARCHITECT_REVIEW"},
        )
        return contracts[0] if contracts else None

    def claim(self, number: int, *, agent: str = "programmer") -> Contract:
        contract = self.load(number)
        if contract.handoff_to != agent:
            raise ValueError(
                f"Kontrakt {number:04d} je předán agentovi {contract.handoff_to!r}, "
                f"nikoli {agent!r}."
            )
        if contract.status not in {"READY_FOR_PROGRAMMER", "CHANGES_REQUESTED"}:
            raise ValueError(
                f"Kontrakt {number:04d} nelze převzít ve stavu {contract.status}."
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
                f"Programátorský výstup lze zapsat pouze ve stavu IN_PROGRESS, "
                f"aktuálně {contract.status}."
            )

        by_number = {int(item["point"]): item for item in notes}
        missing = [point.number for point in contract.points if point.number not in by_number]
        if missing:
            raise ValueError(
                "Programátor musí dodat poznámku ke každému bodu. Chybí body: "
                + ", ".join(map(str, missing))
            )

        global_tests = [str(item).strip() for item in (tests or []) if str(item).strip()]
        for point in contract.points:
            raw = by_number[point.number]
            note = str(raw.get("note", "")).strip()
            if not note:
                raise ValueError(f"Programátorská poznámka k bodu {point.number} je prázdná.")
            point.programmer_note = note
            point.programmer_files = [
                str(item).strip() for item in raw.get("files", []) if str(item).strip()
            ]
            point.programmer_tests = [
                str(item).strip() for item in raw.get("tests", []) if str(item).strip()
            ] or global_tests
            point.status = "IMPLEMENTED"

        contract.programmer_summary = summary.strip()
        contract.status = "READY_FOR_ARCHITECT_REVIEW"
        contract.assigned_to = to_agent
        contract.handoff_to = to_agent
        self.save(contract)
        self.notify(
            to_agent=to_agent,
            from_agent=from_agent,
            contract=contract,
            event="Implementace je hotová a čeká na review.",
        )
        return contract

    def record_architect_review(
        self,
        number: int,
        *,
        approved: bool,
        summary: str,
        reviews: list[dict[str, Any]],
        memory_updates: list[MemoryUpdate] | None = None,
        from_agent: str = "architect",
        to_agent: str = "programmer",
    ) -> Contract:
        contract = self.load(number)
        if contract.status != "READY_FOR_ARCHITECT_REVIEW":
            raise ValueError(
                f"Review lze zapsat pouze ve stavu READY_FOR_ARCHITECT_REVIEW, "
                f"aktuálně {contract.status}."
            )

        by_number = {int(item["point"]): item for item in reviews}
        missing = [point.number for point in contract.points if point.number not in by_number]
        if missing:
            raise ValueError(
                "Architect musí dodat review ke každému bodu. Chybí body: "
                + ", ".join(map(str, missing))
            )

        any_changes = False
        for point in contract.points:
            raw = by_number[point.number]
            review = str(raw.get("review", "")).strip()
            status = str(raw.get("status", "")).upper()
            if status not in {"APPROVED", "CHANGES_REQUESTED"}:
                raise ValueError(
                    f"Neplatný stav review bodu {point.number}: {status!r}."
                )
            if not review:
                raise ValueError(f"Review bodu {point.number} je prázdné.")
            point.architect_review = review
            point.status = status  # type: ignore[assignment]
            any_changes = any_changes or status == "CHANGES_REQUESTED"

        effective_approved = approved and not any_changes
        contract.architect_summary = summary.strip()
        contract.status = "APPROVED" if effective_approved else "CHANGES_REQUESTED"
        contract.assigned_to = "owner" if effective_approved else to_agent
        contract.handoff_to = "owner" if effective_approved else to_agent
        self.save(contract)

        for update in memory_updates or []:
            self.append_memory(update, source=f"CONTRACT {number:04d}")

        self.notify(
            to_agent=contract.handoff_to,
            from_agent=from_agent,
            contract=contract,
            event=(
                "Kontrakt byl schválen."
                if effective_approved
                else "Review požaduje další změny."
            ),
        )
        return contract

    def append_memory(self, update: MemoryUpdate, *, source: str) -> Path:
        relative = update.path.replace("\\", "/").strip("/")
        if not any(pattern.fullmatch(relative) for pattern in ALLOWED_MEMORY_TARGETS):
            raise ValueError(
                f"Nepovolený cíl paměti {update.path!r}. "
                "Povoleno je memory/*.md a agents/*/(MEMORY|WORKING_STATE).md."
            )
        text = update.text.strip()
        if not text:
            raise ValueError("Zápis do paměti nesmí být prázdný.")

        path = (self.project_root / relative).resolve()
        if self.project_root not in path.parents:
            raise ValueError("Cíl paměti leží mimo projekt.")
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
            f"\n\n## {_timestamp()} — CONTRACT {contract.number:04d}\n\n"
            f"- Od: `{from_agent}`\n"
            f"- Stav: `{contract.status}`\n"
            f"- Soubor: `{relative_contract.as_posix()}`\n"
            f"- Zpráva: {event}\n"
        )
        path.write_text(existing + entry, encoding="utf-8")
        return path


def render_contract(contract: Contract) -> str:
    meta = json.dumps(asdict(contract), ensure_ascii=False, indent=2)
    lines = [
        f"# CONTRACT {contract.number:04d} — {contract.title}",
        "",
        f"- **Status:** `{contract.status}`",
        f"- **Vytvořil:** `{contract.created_by}`",
        f"- **Aktuálně řeší:** `{contract.assigned_to}`",
        f"- **Předáno komu:** `{contract.handoff_to}`",
        f"- **Vytvořeno:** `{contract.created_at}`",
        f"- **Aktualizováno:** `{contract.updated_at}`",
        "",
        "## Body kontraktu",
        "",
    ]

    for point in contract.points:
        lines.extend(
            [
                f"### Bod {point.number}",
                "",
                f"**Zadání:** {point.assignment}",
                "",
                "**Akceptační kritéria:**",
            ]
        )
        if point.acceptance_criteria:
            lines.extend(f"- {item}" for item in point.acceptance_criteria)
        else:
            lines.append("- Není výslovně uvedeno; výsledek musí odpovídat zadání bodu.")

        lines.extend(
            [
                "",
                f"**Stav bodu:** `{point.status}`",
                "",
                "**Poznámka programátora:**",
                "",
                point.programmer_note or "_Čeká na implementaci._",
                "",
            ]
        )
        if point.programmer_files:
            lines.append("**Dotčené soubory:**")
            lines.extend(f"- `{item}`" for item in point.programmer_files)
            lines.append("")
        if point.programmer_tests:
            lines.append("**Testy:**")
            lines.extend(f"- {item}" for item in point.programmer_tests)
            lines.append("")
        lines.extend(
            [
                "**Review architekta:**",
                "",
                point.architect_review or "_Čeká na review._",
                "",
            ]
        )

    lines.extend(
        [
            "## Souhrn programátora",
            "",
            contract.programmer_summary or "_Čeká na implementaci._",
            "",
            "## Souhrn architekta",
            "",
            contract.architect_summary or "_Čeká na review._",
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
        raise ValueError("Soubor neobsahuje CONTRACT-META.")
    data = json.loads(match.group(1))
    data["points"] = [ContractPoint(**item) for item in data["points"]]
    return Contract(**data)


def parse_json_response(text: str) -> dict[str, Any]:
    """Načte JSON z čisté odpovědi nebo z ```json ... ``` bloku."""
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    candidate = fenced.group(1) if fenced else stripped
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Agent nevrátil platný JSON. Odpověď nebyla zapsána do kontraktu."
        ) from error
    if not isinstance(value, dict):
        raise ValueError("Kořen odpovědi agenta musí být JSON objekt.")
    return value


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
