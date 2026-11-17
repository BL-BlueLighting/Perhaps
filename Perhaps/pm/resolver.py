"""
doas -su mylife.root
Dependency resolver and transaction planning.

The resolver answers two questions:

* what packages must be installed/upgraded to satisfy a request, in which
  order (dependencies first);
* what installed packages must be removed, and whether doing so would break
  another installed package.

It is deliberately a plain class with a couple of overridable methods; swap it
through ``PackageManager(resolver_class=...)`` if your story wants different
version/conflict policy.

🔎 I am resolving your package 🤔...
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .database import PackageDatabase, PackageRecord, RepositorySet
from .errors import DependencyError, PackageNotFound, VersionError
from .package import Dependency, Package
from .version import compare_versions


@dataclass
class ResolvePlan:
    """Everything a transaction needs, plus human-readable problems."""

    installs: list[Package] = field(default_factory=list)
    removals: list[PackageRecord] = field(default_factory=list)
    optional: list[Dependency] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


class Resolver:
    def __init__(
        self,
        database: PackageDatabase,
        repositories: RepositorySet,
        *,
        allow_downgrade: bool = False,
        needed: bool = False,
    ) -> None:
        self.database = database
        self.repositories = repositories
        self.allow_downgrade = allow_downgrade
        self.needed = needed

    # ---------------------------------------------------------------- helpers
    def _installed_for(self, target: str) -> PackageRecord | None:
        record = self.database.find_by_name(target)
        if record is not None:
            return record
        return self.database.find_satisfier(target)

    def _repo_best(self, target: str) -> Package | None:
        found = self.repositories.best(target)
        return found[1] if found else None

    def _selected_satisfier(
        self,
        dependency: Dependency,
        selected: dict[str, Package],
    ) -> Package | None:
        for package in selected.values():
            if dependency.satisfied_by(package):
                return package
        return None

    def _add_removal(
        self,
        removals: dict[str, PackageRecord],
        record: PackageRecord,
    ) -> None:
        removals.setdefault(record.id, record)

    def _check_downgrade(self, candidate: Package, installed: PackageRecord) -> str | None:
        comparison = compare_versions(candidate.version, installed.package.version)
        if comparison < 0 and not self.allow_downgrade:
            return (
                f"{installed.id}: refusing to downgrade "
                f"{installed.package.version} -> {candidate.version}"
            )
        return None

    # ---------------------------------------------------------------- install
    def resolve_install(
        self,
        targets: list[str],
        *,
        reason: str = "explicit",
        allow_downgrade: bool = False,
        needed: bool = False,
    ) -> ResolvePlan:
        self.allow_downgrade = allow_downgrade or self.allow_downgrade
        self.needed = needed or self.needed
        plan = ResolvePlan()
        selected: dict[str, Package] = {}
        removals: dict[str, PackageRecord] = {}
        visiting: set[str] = set()

        def visit(package: Package, why: str) -> None:
            if package.id in selected:
                return
            if package.id in visiting:
                plan.problems.append(
                    f"dependency cycle detected at {package.id}"
                )
                return
            visiting.add(package.id)
            selected[package.id] = package

            installed = self.database.installed.get(package.id)
            if installed is not None:
                problem = self._check_downgrade(package, installed)
                if problem:
                    plan.problems.append(problem)
                else:
                    self._add_removal(removals, installed)

            for dep_string in package.depends:
                dependency = Dependency.parse(dep_string)
                installed_satisfier = self.database.find_satisfier(dependency)
                if installed_satisfier is not None:
                    # Already satisfied by something installed and not being
                    # replaced by this transaction.
                    if installed_satisfier.id not in removals:
                        continue
                selected_satisfier = self._selected_satisfier(dependency, selected)
                if selected_satisfier is not None:
                    continue

                candidates = self.repositories.candidates_for(dependency)
                if not candidates:
                    plan.problems.append(
                        f"{package.id}: missing dependency "
                        f"{dependency.to_string()} ({why})"
                    )
                    continue
                candidate = candidates[0][1]
                candidate_installed = self.database.installed.get(candidate.id)
                if candidate_installed is not None:
                    problem = self._check_downgrade(candidate, candidate_installed)
                    if problem:
                        plan.problems.append(problem)
                        continue
                    self._add_removal(removals, candidate_installed)
                visit(candidate, f"dependency of {package.id}")

            for optional_string in package.optdepends:
                try:
                    optional = Dependency.parse(optional_string)
                except VersionError:
                    continue
                if (
                    self.database.find_satisfier(optional) is None
                    and self._selected_satisfier(optional, selected) is None
                ):
                    plan.optional.append(optional)
            visiting.discard(package.id)

        for target in targets:
            installed = self._installed_for(target)
            candidate = self._repo_best(target)
            if candidate is None and installed is not None:
                candidate = installed.package
            if candidate is None:
                plan.problems.append(f"target not found: {target}")
                continue

            if (
                installed is not None
                and installed.id == candidate.id
                and self.needed
                and compare_versions(candidate.version, installed.package.version) == 0
            ):
                plan.notes.append(f"{candidate.id}: already up to date")
                continue
            if installed is not None and installed.id != candidate.id:
                if not candidate.replaces_package(installed.package):
                    plan.problems.append(
                        f"{candidate.id} does not replace installed {installed.id}"
                    )
            visit(candidate, "explicit target")

        # Package-declared conflicts / replacements against installed packages.
        for package in list(selected.values()):
            for record in list(self.database.installed.values()):
                if record.id in removals:
                    continue
                if package.id == record.id:
                    continue
                if package.replaces_package(record.package):
                    self._add_removal(removals, record)
                    continue
                if package.conflict_matches(record.package) or record.package.conflict_matches(package):
                    plan.problems.append(
                        f"conflict: {package.id} conflicts with installed "
                        f"{record.id}"
                    )

        selected_list = list(selected.values())
        for index, left in enumerate(selected_list):
            for right in selected_list[index + 1:]:
                if left.id == right.id:
                    continue
                if left.conflict_matches(right) or right.conflict_matches(left):
                    if not left.replaces_package(right) and not right.replaces_package(left):
                        plan.problems.append(
                            f"conflict: {left.id} conflicts with {right.id}"
                        )

        # Removing a package must not break another installed package that
        # stays installed.
        removal_ids = set(removals)
        for record in self.database.installed.values():
            if record.id in removal_ids:
                continue
            for dependency in record.package.dependencies:
                satisfier = self.database.find_satisfier(dependency)
                if satisfier is not None and satisfier.id in removal_ids:
                    replacement = next(
                        (
                            package
                            for package in selected.values()
                            if dependency.satisfied_by(package)
                        ),
                        None,
                    )
                    if replacement is None:
                        plan.problems.append(
                            f"removing {satisfier.id} would break "
                            f"{record.id} ({dependency.to_string()})"
                        )

        plan.removals = list(removals.values())
        plan.installs = self._order_installs(selected)
        plan.problems = _dedupe(plan.problems)
        return plan

    def _order_installs(self, selected: dict[str, Package]) -> list[Package]:
        ordered: list[Package] = []
        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(package: Package) -> None:
            if package.id in visited:
                return
            if package.id in visiting:
                return
            visiting.add(package.id)
            for dependency in package.dependencies:
                for candidate in selected.values():
                    if dependency.satisfied_by(candidate) and candidate.id != package.id:
                        visit(candidate)
                        break
            visiting.discard(package.id)
            visited.add(package.id)
            ordered.append(package)

        for package in selected.values():
            visit(package)
        return ordered

    # ---------------------------------------------------------------- upgrades
    def resolve_upgrade(self, **kwargs) -> ResolvePlan:
        targets = []
        for record in self.database.installed.values():
            candidates = self.repositories.candidates_for(record.package.id)
            if not candidates:
                candidates = self.repositories.candidates_for(record.package.name)
            if any(
                compare_versions(package.version, record.package.version) > 0
                for _repository, package in candidates
            ):
                targets.append(record.package.id)
        kwargs.setdefault("needed", True)
        return self.resolve_install(targets, **kwargs)

    # ---------------------------------------------------------------- removal
    def resolve_remove(
        self,
        targets: list[str],
        *,
        cascade: bool = False,
        recursive: bool = False,
    ) -> ResolvePlan:
        plan = ResolvePlan()
        removals: dict[str, PackageRecord] = {}
        for target in targets:
            record = self.database.find_by_name(target)
            if record is None:
                plan.problems.append(f"target not installed: {target}")
            else:
                removals[record.id] = record

        if cascade:
            changed = True
            while changed:
                changed = False
                for record in self.database.installed.values():
                    if record.id in removals:
                        continue
                    if any(dependent in removals for dependent in record.required_by):
                        removals[record.id] = record
                        changed = True
        else:
            for record in self.database.installed.values():
                if record.id in removals:
                    continue
                for dependency in record.package.dependencies:
                    satisfier = self.database.find_satisfier(dependency)
                    if satisfier is not None and satisfier.id in removals:
                        plan.problems.append(
                            f"removing {satisfier.id} would break "
                            f"{record.id} ({dependency.to_string()})"
                        )

        if recursive:
            changed = True
            while changed:
                changed = False
                remaining = [
                    record
                    for record in self.database.installed.values()
                    if record.id not in removals
                ]
                removal_ids = set(removals)
                for record in remaining:
                    if record.reason != "dependency":
                        continue
                    needed = False
                    for dependent in self.database.installed.values():
                        if dependent.id in removal_ids:
                            continue
                        if any(
                            satisfier.id == record.id
                            for satisfier in [
                                self.database.find_satisfier(dependency)
                                for dependency in dependent.package.dependencies
                            ]
                            if satisfier is not None
                        ):
                            needed = True
                            break
                    if not needed:
                        removals[record.id] = record
                        changed = True

        plan.removals = list(removals.values())
        plan.problems = _dedupe(plan.problems)
        return plan

    # ------------------------------------------------------------------- deps
    def check_dependencies(self) -> list[str]:
        return self.database.missing_dependencies()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
