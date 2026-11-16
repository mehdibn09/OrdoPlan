"""Ordonnancement mono-opération, machines alternatives, réglages dépendant de la séquence."""
import time
from ortools.sat.python import cp_model
from src.schemas.pydantic_models import Instance, Operation, Schedule
from src.solver.checker import check_schedule, metrics


def merged_windows(windows):
    """Deux arrêts superposés forment une indisponibilité, pas deux tâches concurrentes."""
    result=[]
    for window in sorted(windows,key=lambda w:(w.start,w.end)):
        if result and window.start<=result[-1][1]:
            result[-1]=(result[-1][0],max(result[-1][1],window.end))
        else:
            result.append((window.start,window.end))
    return result


def solve(instance: Instance, time_limit: float = 20.0) -> Schedule:
    started = time.monotonic()
    model = cp_model.CpModel()
    horizon = instance.horizon
    starts, ends, selected, setups, intervals = {}, {}, {}, {}, {}
    frozen = {f.order_id: f for f in instance.frozen}
    for o in instance.orders:
        starts[o.id] = model.new_int_var(0, horizon, f"start_{o.id}")
        ends[o.id] = model.new_int_var(0, horizon, f"end_{o.id}")
        model.add(ends[o.id] == starts[o.id] + o.duration)
        model.add(starts[o.id] >= o.release)
        if o.id not in frozen:
            model.add(starts[o.id] >= instance.now)
        for mid in o.eligible:
            x = model.new_bool_var(f"use_{o.id}_{mid}")
            selected[o.id, mid] = x
            st = model.new_int_var(0, max(instance.setup.values(), default=0), f"setup_{o.id}_{mid}")
            setups[o.id, mid] = st
            block = model.new_int_var(0, horizon, f"block_{o.id}_{mid}")
            size = model.new_int_var(o.duration, o.duration + max(instance.setup.values(), default=0), f"size_{o.id}_{mid}")
            model.add(block == starts[o.id] - st).only_enforce_if(x)
            if o.id not in frozen:
                model.add(block >= instance.now).only_enforce_if(x)
            model.add(size == o.duration + st)
            intervals[o.id, mid] = model.new_optional_interval_var(block, size, ends[o.id], x, f"interval_{o.id}_{mid}")
            model.add(st == 0).only_enforce_if(x.Not())
        model.add_exactly_one(selected[o.id, mid] for mid in o.eligible)
        if o.id in frozen:
            f = frozen[o.id]
            if f.machine not in o.eligible:
                model.add(False)
            else:
                model.add(selected[o.id, f.machine] == 1)
                model.add(starts[o.id] == f.start)
                model.add(ends[o.id] == f.end)
                model.add(setups[o.id, f.machine] == f.setup)
    for machine in instance.machines:
        jobs = [o for o in instance.orders if machine.id in o.eligible]
        if not jobs:
            continue
        arcs = []
        empty = model.new_bool_var(f"empty_{machine.id}")
        arcs.append((0, 0, empty))
        model.add(sum(selected[o.id, machine.id] for o in jobs) == 0).only_enforce_if(empty)
        blocks = [intervals[o.id, machine.id] for o in jobs]
        for start,end in merged_windows(machine.unavailable):
            blocks.append(model.new_fixed_size_interval_var(start, end-start, f"down_{machine.id}_{start}"))
        model.add_no_overlap(blocks)
        for i, o in enumerate(jobs, 1):
            x = selected[o.id, machine.id]
            arcs.append((i, i, x.Not()))
            first = model.new_bool_var(f"first_{machine.id}_{i}")
            last = model.new_bool_var(f"last_{machine.id}_{i}")
            arcs.extend([(0, i, first), (i, 0, last)])
            model.add(setups[o.id, machine.id] == instance.changeover(machine.initial_family, o.family)).only_enforce_if(first)
            for j, other in enumerate(jobs, 1):
                if i == j:
                    continue
                arc = model.new_bool_var(f"arc_{machine.id}_{i}_{j}")
                arcs.append((i, j, arc))
                change = instance.changeover(o.family, other.family)
                model.add(starts[other.id] >= ends[o.id] + change).only_enforce_if(arc)
                model.add(setups[other.id, machine.id] == change).only_enforce_if(arc)
        model.add_circuit(arcs)
    resources = {}
    for o in instance.orders:
        iv = model.new_interval_var(starts[o.id], o.duration, ends[o.id], f"process_{o.id}")
        for r in (o.tool, o.operator):
            if r:
                resources.setdefault(r, []).append(iv)
    for resource, blocks in resources.items():
        for start,end in merged_windows(instance.resource_unavailable.get(resource, [])):
            blocks.append(model.new_fixed_size_interval_var(start, end-start, f"unavailable_{resource}_{start}"))
        model.add_no_overlap(blocks)
    tardiness = []
    for o in instance.orders:
        late = model.new_int_var(0, horizon, f"late_{o.id}")
        model.add_max_equality(late, [0, ends[o.id] - o.due])
        tardiness.append(o.priority * late)
    primary = sum(tardiness)
    displacement = []
    for old in instance.baseline:
        if old.order_id not in starts:
            continue
        delta = model.new_int_var(0, horizon, f"delta_{old.order_id}")
        model.add_abs_equality(delta, starts[old.order_id]-old.start)
        same = selected.get((old.order_id, old.machine))
        displacement.append(delta + (60 * (1-same) if same is not None else 60))
    stability = sum(displacement)
    makespan = model.new_int_var(0, horizon, "makespan")
    model.add_max_equality(makespan, list(ends.values()))
    objectives = [primary] + ([stability] if displacement else []) + [makespan]
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 42
    all_optimal = True
    best, bound = None, None
    for stage, objective in enumerate(objectives):
        remaining = max(0, time_limit - (time.monotonic()-started))
        if remaining < 0.02:
            all_optimal = False
            break
        solver.parameters.max_time_in_seconds = remaining if stage == len(objectives)-1 else max(.02, remaining*.65)
        model.minimize(objective)
        status = solver.solve(model)
        name = solver.status_name(status)
        if stage == 0:
            bound = solver.best_objective_bound
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if best is None:
                return Schedule(status=name, instance_id=instance.id, elapsed_seconds=time.monotonic()-started, violations=["Aucune solution trouvée : vérifier horizon, gel, éligibilités, matières et indisponibilités. Ne pas assouplir automatiquement."])
            all_optimal = False
            break
        all_optimal &= status == cp_model.OPTIMAL
        ops = []
        for o in instance.orders:
            mid = next(m for m in o.eligible if solver.value(selected[o.id, m]))
            ops.append(Operation(order_id=o.id, machine=mid, start=solver.value(starts[o.id]), end=solver.value(ends[o.id]), setup=solver.value(setups[o.id, mid])))
        best = sorted(ops, key=lambda p: (p.machine, p.start))
        model.add(objective <= int(round(solver.objective_value)))
    if best is None:
        return Schedule(status="UNKNOWN", instance_id=instance.id, elapsed_seconds=time.monotonic()-started)
    errors = check_schedule(instance, best)
    return Schedule(status="OPTIMAL" if all_optimal else "FEASIBLE", operations=best, instance_id=instance.id, violations=errors, primary_bound=bound, elapsed_seconds=time.monotonic()-started, **metrics(instance, best))
