import pytest
from pydantic import ValidationError
from src.schemas.pydantic_models import Instance, Window
from src.solver.cp_sat import solve
from src.solver.checker import check_schedule, metrics, diff_schedules
from src.solver.baselines import greedy


def test_optimal_and_independent_check(instance):
    result=solve(instance,3)
    assert result.status=="OPTIMAL"
    assert not check_schedule(instance,result.operations)
    assert result.weighted_tardiness==0
    assert result.primary_bound==0


@pytest.mark.parametrize("index",range(10))
def test_reference_instances(index):
    from src.config import DATA
    value=Instance.model_validate_json((DATA/"instances"/f"instance-{index:02d}.json").read_text())
    result=solve(value,1)
    assert result.operations and not check_schedule(value,result.operations)


@pytest.mark.parametrize("rule",["FIFO","EDD"])
def test_baseline_feasible(instance,rule):
    result=greedy(instance,rule)
    assert result and not check_schedule(instance,result)


def test_unique_tool_and_operator(instance):
    for order in instance.orders:
        order.operator="OP-01"
    instance.horizon=1000
    result=solve(instance,2)
    assert result.operations and not check_schedule(instance,result.operations)
    for a,b in zip(sorted(result.operations,key=lambda p:p.start),sorted(result.operations,key=lambda p:p.start)[1:]):
        assert a.end<=b.start


def test_operator_absence_and_material(instance):
    instance.orders[0].operator="OP-01"
    instance.orders[0].release=100
    instance.resource_unavailable={"OP-01":[Window(start=100,end=200)]}
    result=solve(instance,2)
    p=next(p for p in result.operations if p.order_id==instance.orders[0].id)
    assert p.start>=200
    assert not check_schedule(instance,result.operations)


def test_frozen_replan(instance):
    initial=solve(instance,2)
    instance.baseline=initial.operations
    instance.now=90
    instance.frozen=[p for p in initial.operations if p.start-p.setup<90]
    instance.machines[0].unavailable=[Window(start=300,end=450)]
    result=solve(instance,3)
    assert result.operations
    assert not check_schedule(instance,result.operations)
    assert all(f in result.operations for f in instance.frozen)
    assert diff_schedules(initial.operations,result.operations,instance)["moved_count"]>=0


def test_ongoing_breakdown_conflict_is_infeasible(instance):
    initial=solve(instance,2)
    p=initial.operations[0]
    instance.now=p.start+1
    instance.frozen=[x for x in initial.operations if x.start-x.setup<instance.now]
    next(m for m in instance.machines if m.id==p.machine).unavailable=[Window(start=instance.now,end=instance.now+120)]
    result=solve(instance,1)
    assert result.status=="INFEASIBLE"
    assert not result.operations


@pytest.mark.parametrize("mutation",["missing","duration","machine","setup","overlap","material","frozen","downtime","tool"])
def test_checker_detects_corruption(instance,mutation):
    operations=solve(instance,2).operations
    p=operations[0]
    if mutation=="missing":
        operations.pop()
    elif mutation=="duration":
        p.end+=1
    elif mutation=="machine":
        p.machine="UNKNOWN"
    elif mutation=="setup":
        p.setup+=1
    elif mutation=="overlap":
        other=next(x for x in operations if x.machine==p.machine and x!=p)
        other.end=other.end-other.start+p.start;other.start=p.start
    elif mutation=="material":
        next(o for o in instance.orders if o.id==p.order_id).release=p.end
    elif mutation=="frozen":
        instance.frozen=[p.model_copy(deep=True)];p.start+=1;p.end+=1
    elif mutation=="downtime":
        next(m for m in instance.machines if m.id==p.machine).unavailable=[Window(start=p.start,end=p.end)]
    elif mutation=="tool":
        for o in instance.orders:
            o.tool="UNIQUE"
    assert check_schedule(instance,operations)


def test_no_source_no_solver(instance):
    raw=instance.model_dump()
    del raw["orders"][0]["sources"]["duration"]
    with pytest.raises(ValidationError):
        Instance.model_validate(raw)


def test_objective_is_real_metrics(instance):
    result=solve(instance,2)
    assert metrics(instance,result.operations)["weighted_tardiness"]==result.weighted_tardiness


def test_bound_status_on_small_budget(instance):
    result=solve(instance,.001)
    assert result.status=="UNKNOWN" and not result.operations


def test_overlapping_unavailability_is_merged(instance):
    instance.machines[0].unavailable=[Window(start=0,end=60),Window(start=30,end=90)]
    instance.resource_unavailable={"OUTIL-UNIQUE":[Window(start=0,end=60),Window(start=30,end=90)]}
    result=solve(instance,2)
    assert result.operations and not check_schedule(instance,result.operations)
