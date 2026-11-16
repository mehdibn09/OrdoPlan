"""Heuristiques FIFO et EDD, réalisables et soumises au même contrôleur."""
from src.schemas.pydantic_models import Operation
from src.solver.checker import overlap


def greedy(instance, rule="EDD"):
    operations = list(instance.frozen)
    frozen = {p.order_id for p in operations}
    jobs = [o for o in instance.orders if o.id not in frozen]
    jobs = sorted(jobs, key=lambda o: (o.due, o.id) if rule == "EDD" else (o.release, o.id))
    for o in jobs:
        candidates = []
        for mid in o.eligible:
            machine = next(m for m in instance.machines if m.id == mid)
            prior = sorted([p for p in operations if p.machine == mid], key=lambda p: p.end)
            before_family = next((v.family for v in instance.orders if prior and v.id == prior[-1].order_id), machine.initial_family)
            setup = instance.changeover(before_family, o.family)
            earliest = max(o.release, instance.now, (prior[-1].end if prior else 0)+setup)
            for start in range(earliest, instance.horizon-o.duration+1):
                end = start+o.duration
                blocked = any(overlap((start-setup, end), (w.start, w.end)) for w in machine.unavailable)
                for p in operations:
                    other = next(x for x in instance.orders if x.id == p.order_id)
                    shared = (o.tool and o.tool == other.tool) or (o.operator and o.operator == other.operator)
                    blocked |= bool(shared and overlap((start, end), (p.start, p.end)))
                for r in (o.tool, o.operator):
                    blocked |= any(overlap((start, end), (w.start, w.end)) for w in instance.resource_unavailable.get(r, []))
                if not blocked:
                    candidates.append(Operation(order_id=o.id, machine=mid, start=start, end=end, setup=setup))
                    break
        if not candidates:
            return []
        operations.append(min(candidates, key=lambda p: (p.end, p.machine)))
    return sorted(operations, key=lambda p: (p.machine, p.start))
