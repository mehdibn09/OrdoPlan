"""Contrôleur indépendant : aucune dépendance OR-Tools ni correction silencieuse."""
from src.schemas.pydantic_models import Instance, Operation


def overlap(a, b):
    return max(a[0], b[0]) < min(a[1], b[1])


def check_schedule(instance: Instance, operations: list[Operation]) -> list[str]:
    errors = []
    orders = {o.id: o for o in instance.orders}
    machines = {m.id: m for m in instance.machines}
    ids = [p.order_id for p in operations]
    if len(ids) != len(set(ids)) or set(ids) != set(orders):
        errors.append("Couverture : chaque OF doit apparaître exactement une fois")
    for p in operations:
        o = orders.get(p.order_id)
        if o is None or p.machine not in machines:
            errors.append("OF ou machine inconnu")
            continue
        if p.machine not in o.eligible:
            errors.append(f"{o.id}: machine non éligible")
        if p.end - p.start != o.duration:
            errors.append(f"{o.id}: durée incorrecte")
        frozen = next((f for f in instance.frozen if f.order_id == o.id), None)
        minimum = o.release if frozen else max(o.release, instance.now)
        if p.start < minimum or p.start-p.setup < (0 if frozen else instance.now) or p.end > instance.horizon:
            errors.append(f"{o.id}: disponibilité matière, instant courant ou horizon")
        if frozen and p != frozen:
            errors.append(f"{o.id}: opération gelée modifiée")
        for w in machines[p.machine].unavailable:
            if overlap((p.start-p.setup, p.end), (w.start, w.end)):
                errors.append(f"{o.id}: indisponibilité machine")
    for mid, machine in machines.items():
        sequence = sorted((p for p in operations if p.machine == mid and p.order_id in orders), key=lambda p: p.start)
        previous_family = machine.initial_family
        previous_end = 0
        for p in sequence:
            family = orders[p.order_id].family
            try:
                expected = instance.changeover(previous_family, family)
            except ValueError as e:
                errors.append(str(e))
                expected = -1
            if p.setup != expected:
                errors.append(f"{p.order_id}: changement de série incorrect")
            if p.start - p.setup < previous_end:
                errors.append(f"{mid}: chevauchement production/réglage")
            previous_family, previous_end = family, p.end
    resources = {}
    for p in operations:
        o = orders.get(p.order_id)
        if not o:
            continue
        for r in (o.tool, o.operator):
            if r:
                resources.setdefault(r, []).append(p)
    for r, uses in resources.items():
        for i, a in enumerate(uses):
            for b in uses[i+1:]:
                if overlap((a.start, a.end), (b.start, b.end)):
                    errors.append(f"{r}: ressource unique en chevauchement")
            for w in instance.resource_unavailable.get(r, []):
                if overlap((a.start, a.end), (w.start, w.end)):
                    errors.append(f"{r}: indisponibilité de ressource")
    return errors


def metrics(instance, operations):
    by_id = {o.id: o for o in instance.orders}
    baseline = {p.order_id: p for p in instance.baseline}
    return {
        "weighted_tardiness": sum(by_id[p.order_id].priority * max(0, p.end - by_id[p.order_id].due) for p in operations),
        "makespan": max((p.end for p in operations), default=0),
        "stability": sum(abs(p.start-baseline[p.order_id].start) + 60 * (p.machine != baseline[p.order_id].machine) for p in operations if p.order_id in baseline),
    }


def diff_schedules(old, new, instance):
    old_map = {p.order_id: p for p in old}
    orders = {o.id: o for o in instance.orders}
    changes = []
    delays = []
    for p in new:
        before = old_map.get(p.order_id)
        if before is None or before.machine != p.machine or before.start != p.start:
            changes.append({"order_id": p.order_id, "before": before.model_dump() if before else None, "after": p.model_dump()})
        delay = max(0, p.end-orders[p.order_id].due)
        if delay:
            delays.append({"order_id": p.order_id, "minutes": delay, "weighted_minutes": delay*orders[p.order_id].priority})
    return {"moved_count": sum(c["before"] is not None for c in changes), "added_count": sum(c["before"] is None for c in changes), "changes": changes, "delays": delays}
