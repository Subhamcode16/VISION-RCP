"""Vision-RCP Dependency Graph — DAG-based process group management."""

from __future__ import annotations

import asyncio
import graphlib
import logging
from typing import Any

from .models import ManagedProcess, ProcessGroup
from .process_manager import ProcessManager
from .protocol import ProcessState

logger = logging.getLogger("rcp.dependency_graph")


class DependencyGraphEngine:
    """Manages process groups with dependency ordering using topological sort."""

    def __init__(self, process_manager: ProcessManager):
        self._pm = process_manager
        self._groups: dict[str, ProcessGroup] = {}

    def register_group(self, name: str, process_defs: dict[str, dict[str, Any]]) -> None:
        """Register a process group from config.

        process_defs example:
        {
            "database": {"cmd": "postgres", "args": [...], "depends_on": []},
            "api-server": {"cmd": "node", "args": [...], "depends_on": ["database"]},
            "frontend": {"cmd": "npm", "args": [...], "depends_on": ["api-server"]},
        }
        """
        group = ProcessGroup(name=name)
        for proc_name, definition in process_defs.items():
            group.processes[proc_name] = ManagedProcess(
                name=proc_name,
                cmd=definition.get("cmd", ""),
                args=definition.get("args", []),
                env=definition.get("env", {}),
                cwd=definition.get("cwd"),
                depends_on=definition.get("depends_on", []),
                auto_restart=definition.get("auto_restart", False),
                max_restarts=definition.get("max_restarts", 5),
                group=name,
            )

        # Validate: no cycles
        dep_graph = {}
        for proc_name, proc in group.processes.items():
            dep_graph[proc_name] = set(proc.depends_on)

        try:
            sorter = graphlib.TopologicalSorter(dep_graph)
            sorter.prepare()
        except graphlib.CycleError as e:
            raise ValueError(f"Circular dependency in group '{name}': {e}") from e

        self._groups[name] = group
        logger.info("Registered process group '%s' with %d processes",
                     name, len(group.processes))

    async def start_group(self, group_name: str,
                          on_event: Any | None = None) -> list[dict[str, Any]]:
        """Start all processes in a group respecting dependency order.

        Uses TopologicalSorter's parallel-ready API to start independent
        processes concurrently while respecting dependency chains.
        """
        group = self._groups.get(group_name)
        if not group:
            raise ValueError(f"Unknown process group: '{group_name}'")

        # Build dependency graph
        dep_graph: dict[str, set[str]] = {}
        for proc_name, proc in group.processes.items():
            dep_graph[proc_name] = set(proc.depends_on)

        sorter = graphlib.TopologicalSorter(dep_graph)
        sorter.prepare()

        results: list[dict[str, Any]] = []

        while sorter.is_active():
            ready = sorter.get_ready()

            # Start all ready processes concurrently
            tasks = []
            for proc_name in ready:
                proc_def = group.processes[proc_name]
                tasks.append(self._start_single(proc_name, proc_def, group_name))

            started = await asyncio.gather(*tasks, return_exceptions=True)

            for proc_name, result in zip(ready, started):
                if isinstance(result, Exception):
                    logger.error("Failed to start '%s' in group '%s': %s",
                                 proc_name, group_name, result)
                    results.append({
                        "name": proc_name,
                        "status": "failed",
                        "error": str(result),
                    })
                else:
                    results.append({
                        "name": proc_name,
                        "status": "running",
                        "pid": result.pid,
                    })

                sorter.done(proc_name)

        logger.info("Group '%s' startup complete: %d processes", group_name, len(results))
        return results

    async def _start_single(self, name: str, proc: ManagedProcess,
                            group_name: str) -> ManagedProcess:
        """Start a single process from a group definition."""
        # Wait briefly to ensure dependencies are actually ready
        for dep_name in proc.depends_on:
            dep = self._pm.get_by_name(dep_name)
            if dep and dep.state != ProcessState.RUNNING:
                # Wait up to 30s for dependency to be ready
                for _ in range(60):
                    await asyncio.sleep(0.5)
                    dep = self._pm.get_by_name(dep_name)
                    if dep and dep.state == ProcessState.RUNNING:
                        break
                else:
                    raise RuntimeError(
                        f"Dependency '{dep_name}' did not reach RUNNING state"
                    )

        return await self._pm.spawn(
            name=name,
            cmd=proc.cmd,
            args=proc.args,
            env=proc.env,
            cwd=proc.cwd,
            depends_on=proc.depends_on,
            auto_restart=proc.auto_restart,
            max_restarts=proc.max_restarts,
            group=group_name,
        )

    async def stop_group(self, group_name: str) -> list[dict[str, Any]]:
        """Stop all processes in a group in REVERSE dependency order."""
        group = self._groups.get(group_name)
        if not group:
            raise ValueError(f"Unknown process group: '{group_name}'")

        # Build reverse dependency graph
        dep_graph: dict[str, set[str]] = {}
        for proc_name, proc in group.processes.items():
            dep_graph[proc_name] = set(proc.depends_on)

        # Get topological order then reverse it
        sorter = graphlib.TopologicalSorter(dep_graph)
        order = list(sorter.static_order())
        order.reverse()

        results: list[dict[str, Any]] = []

        for proc_name in order:
            proc = self._pm.get_by_name(proc_name)
            if proc and proc.pid and proc.state == ProcessState.RUNNING:
                success = await self._pm.kill(proc.pid)
                results.append({
                    "name": proc_name,
                    "status": "stopped" if success else "failed",
                    "pid": proc.pid,
                })
            else:
                results.append({
                    "name": proc_name,
                    "status": "already_stopped",
                })

        logger.info("Group '%s' shutdown complete", group_name)
        return results

    def get_graph_status(self) -> dict[str, Any]:
        """Get the current state of all groups and their dependency graphs."""
        graph_data: dict[str, Any] = {}
        for group_name, group in self._groups.items():
            nodes = []
            edges = []
            for proc_name, proc in group.processes.items():
                live = self._pm.get_by_name(proc_name)
                nodes.append({
                    "id": proc_name,
                    "state": live.state.value if live else "unknown",
                    "pid": live.pid if live else None,
                })
                for dep in proc.depends_on:
                    edges.append({"from": dep, "to": proc_name})

            graph_data[group_name] = {
                "name": group_name,
                "nodes": nodes,
                "edges": edges,
            }

        return graph_data

    def list_groups(self) -> list[str]:
        return list(self._groups.keys())
