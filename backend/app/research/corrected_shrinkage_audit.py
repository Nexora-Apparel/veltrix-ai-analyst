"""Pre-registered, retrospective shrinkage diagnostic. Never admission evidence."""
from __future__ import annotations

import math
from datetime import datetime
from statistics import median
from typing import Any

from app.models.hierarchical_poisson import HierarchicalGoalResult, fit_hierarchical_poisson

# PRE-REGISTRATION: frozen before inspecting results.
REFERENCE_K = (0.5, 2.0)
FOLD_RULE = "kickoff-date expanding windows: first 60%, 70%, 80%, 90% unique dates train; next 10% dates test; all boundaries are exclusive/inclusive as recorded"
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20261121
MAX_ITERATIONS = 4000
OPTIMIZER_TOLERANCE = 1e-7
HOME_ADVANTAGE_TREATMENT = "unpenalized in archived and both reference fits"
ARCHIVED_CONFIG = {"team_ridge": 0.5, "competition_ridge": 0.5, "half_life_days": 365.0}
METRICS = ("1X2_log_loss", "1X2_multiclass_brier")
EXPECTED_ZIP_HASHES = {
    "stage6": "3a2ebfb7dd94899bc1cf5000bb365c440753afcfa474869a733bbeeda0a1ad81",
    "forecast": "44164d6e9ead148b6fa0e663f81bde18ad5f75e839143e408a2ecce98cc7f16f",
}
EXPECTED_DATASET_SHA = "80148b3f0f42e70d94391d9283c42f35b5b92e1631a9a1cb7baee899373dad0c"
EXPECTED_TRAINING_SHA = "d70ee34940c8fc6681f3cd5751d4fdcc2e876b307fe388d9f3a792c73e34b262"


def _dt(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("naive timestamp")
    return result


def _weights(rows: list[dict[str, Any]], cutoff: datetime) -> list[float]:
    return [math.exp(-math.log(2) * max(0, (cutoff-_dt(r["kickoff_at"])).total_seconds()/86400) / 365.0) for r in rows]


def _fold_weight_and_mean_goals(rows: list[dict[str, Any]], cutoff: datetime) -> tuple[float, float]:
    """Return W and weighted mean goals per team per match for this fold."""
    weights = _weights(rows, cutoff)
    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError("FOLD_WEIGHT_NOT_POSITIVE")
    weighted_goals = sum(
        weight * (int(row["label"]["home_goals"]) + int(row["label"]["away_goals"]))
        for row, weight in zip(rows, weights)
    )
    mu = weighted_goals / (2.0 * total_weight)
    if mu <= 0:
        raise ValueError("FOLD_MEAN_GOALS_NOT_POSITIVE")
    return total_weight, mu


def _ridge_for_unnormalized_prior(k: float, mu: float, total_weight: float) -> tuple[float, float]:
    """Convert summed-objective tau values to this model's averaged-objective ridge."""
    if k <= 0 or mu <= 0 or total_weight <= 0:
        raise ValueError("INVALID_REGULARIZATION_SCALE")
    return k * mu / total_weight, k * 2.0 * mu / total_weight


def _fit_for_audit(
    rows: list[dict[str, Any]], cutoff: datetime, *, k: float | None,
    archived: bool = False,
) -> dict[str, Any]:
    total_weight, mu = _fold_weight_and_mean_goals(rows, cutoff)
    if archived:
        team_ridge = ARCHIVED_CONFIG["team_ridge"]
        competition_ridge = ARCHIVED_CONFIG["competition_ridge"]
    else:
        assert k is not None
        team_ridge, competition_ridge = _ridge_for_unnormalized_prior(k, mu, total_weight)
    try:
        model = fit_hierarchical_poisson(
            [_result(row) for row in rows],
            as_of=cutoff,
            half_life_days=365,
            team_ridge=team_ridge,
            competition_ridge=competition_ridge,
            max_iterations=MAX_ITERATIONS,
            tolerance=OPTIMIZER_TOLERANCE,
            optimizer="lbfgs",
        )
    except ArithmeticError as exc:
        return {
            "model": None, "solver": "L-BFGS", "converged": False, "iterations": None,
            "gradient_norm": None, "error": str(exc),
            "total_recency_weight": total_weight,
            "weighted_mean_goals_per_team_match": mu,
            "team_ridge_averaged_objective": team_ridge,
            "competition_ridge_averaged_objective": competition_ridge,
        }
    return {
        "model": model, "solver": "L-BFGS", "converged": model.optimizer_converged,
        "iterations": model.optimizer_iterations,
        "gradient_norm": model.optimizer_gradient_norm, "error": None,
        "total_recency_weight": total_weight,
        "weighted_mean_goals_per_team_match": mu,
        "team_ridge_averaged_objective": team_ridge,
        "competition_ridge_averaged_objective": competition_ridge,
    }


def _result(row: dict[str, Any]) -> HierarchicalGoalResult:
    label = row["label"]
    return HierarchicalGoalResult(str(row["fixture_id"]), _dt(row["kickoff_at"]), str(row["competition_id"]), str(row["home_team_id"]), str(row["away_team_id"]), int(label["home_goals"]), int(label["away_goals"]))


def _pois(lam: float, cap: int = 12) -> list[float]:
    p=[math.exp(-lam)]
    for i in range(1,cap+1):
        p.append(p[-1]*lam/i)
    return p


def _probabilities(home: float, away: float) -> tuple[float,float,float]:
    hp, ap = _pois(home), _pois(away)
    h=d=a=0.0
    for i,x in enumerate(hp):
        for j,y in enumerate(ap):
            if i>j: h += x*y
            elif i==j: d += x*y
            else: a += x*y
    total=h+d+a
    return h/total,d/total,a/total


def _metrics(rows: list[dict[str, Any]], model: Any) -> dict[str,float]:
    losses=[]; briers=[]
    for row in rows:
        rates=model.predict(str(row["home_team_id"]),str(row["away_team_id"]),str(row["competition_id"]))
        probs=_probabilities(rates.home_lambda,rates.away_lambda)
        hg,ag=int(row["label"]["home_goals"]),int(row["label"]["away_goals"])
        actual=0 if hg>ag else (1 if hg==ag else 2)
        losses.append(-math.log(max(probs[actual],1e-15)))
        briers.append(sum((p-(1.0 if i==actual else 0.0))**2 for i,p in enumerate(probs)))
    return {"1X2_log_loss":sum(losses)/len(losses),"1X2_multiclass_brier":sum(briers)/len(briers),"n":len(rows)}


def _dispersion(rows: list[dict[str, Any]], model: Any) -> dict[str,Any]:
    hs=[];as_=[];ps=[]
    for row in rows:
        rate=model.predict(str(row["home_team_id"]),str(row["away_team_id"]),str(row["competition_id"]))
        hs.append(rate.home_lambda);as_.append(rate.away_lambda);ps.append(_probabilities(rate.home_lambda,rate.away_lambda)[0])
    def summary(values: list[float]) -> dict[str,float]:
        return {"mean":sum(values)/len(values),"sd":(sum((x-sum(values)/len(values))**2 for x in values)/len(values))**0.5,"min":min(values),"max":max(values)}
    return {"expected_home_goals":summary(hs),"expected_away_goals":summary(as_),"p_home":summary(ps),"n":len(rows)}


def _weighted_summary(values: list[tuple[float,int]]) -> dict[str,Any]:
    """Return ordinary and match-count-weighted median/IQR for team ratios."""
    ordered=sorted(value for value,_ in values)
    if not ordered:
        return {
            "n": 0, "median": None, "q1": None, "q3": None,
            "weighted_median": None, "weighted_q1": None, "weighted_q3": None,
        }
    def quantile(items: list[float], q: float) -> float:
        position=(len(items)-1)*q
        lower=int(position); upper=min(lower+1,len(items)-1)
        return items[lower]+(items[upper]-items[lower])*(position-lower)
    pairs=sorted((value,weight) for value,weight in values if weight>0)
    def weighted_quantile(q: float) -> float:
        total=sum(weight for _,weight in pairs)
        threshold=q*total
        cumulative=0
        for value,weight in pairs:
            cumulative+=weight
            if cumulative>=threshold:
                return value
        return pairs[-1][0]
    return {
        "n": len(ordered),
        "median": median(ordered),
        "q1": quantile(ordered,.25),
        "q3": quantile(ordered,.75),
        "weighted_median": weighted_quantile(.5),
        "weighted_q1": weighted_quantile(.25),
        "weighted_q3": weighted_quantile(.75),
    }


def _centered_team_ratio_summary(archived: Any, reference: Any) -> dict[str,Any]:
    """Compare absolute centred effects; omit undefined near-zero references."""
    def centred(model: Any, effects: dict[str,float]) -> dict[str,float]:
        counts=model.team_match_counts
        total=sum(counts.values())
        mean_effect=sum(effects[team]*counts[team] for team in effects)/total
        return {team: effects[team]-mean_effect for team in effects}
    archived_attack=centred(archived,archived.attack)
    reference_attack=centred(reference,reference.attack)
    archived_defence=centred(archived,archived.defence)
    reference_defence=centred(reference,reference.defence)
    attack=[]; defence=[]; attack_sign_reversals=0; defence_sign_reversals=0
    omitted_attack=0; omitted_defence=0
    for team in sorted(set(archived_attack)&set(reference_attack)):
        count=min(archived.team_match_counts.get(team,0),reference.team_match_counts.get(team,0))
        if abs(reference_attack[team])<=1e-8:
            omitted_attack+=1
        else:
            attack.append((abs(archived_attack[team])/abs(reference_attack[team]),count))
            if archived_attack[team]*reference_attack[team]<0:
                attack_sign_reversals+=1
        if abs(reference_defence[team])<=1e-8:
            omitted_defence+=1
        else:
            defence.append((abs(archived_defence[team])/abs(reference_defence[team]),count))
            if archived_defence[team]*reference_defence[team]<0:
                defence_sign_reversals+=1
    return {
        "ratio_definition": "absolute match-count-centred archived effect divided by absolute match-count-centred reference effect; reference magnitudes <=1e-8 omitted",
        "attack": _weighted_summary(attack),
        "defence": _weighted_summary(defence),
        "attack_omitted_near_zero_reference": omitted_attack,
        "defence_omitted_near_zero_reference": omitted_defence,
        "attack_sign_reversals": attack_sign_reversals,
        "defence_sign_reversals": defence_sign_reversals,
    }


def _centered_team_effects(archived: Any, reference: Any) -> list[dict[str,Any]]:
    """Return canonical team IDs and match-count-centred identified effects only."""
    def centre(model: Any, effects: dict[str,float]) -> dict[str,float]:
        counts=model.team_match_counts
        total=sum(counts[team] for team in effects)
        mean_effect=sum(effects[team]*counts[team] for team in effects)/total
        return {team: effects[team]-mean_effect for team in effects}
    aa=centre(archived,archived.attack)
    ra=centre(reference,reference.attack)
    ad=centre(archived,archived.defence)
    rd=centre(reference,reference.defence)
    return [
        {
            "canonical_team_id": team,
            "archived_attack_centered": aa[team],
            "reference_attack_centered": ra[team],
            "archived_defence_centered": ad[team],
            "reference_defence_centered": rd[team],
        }
        for team in sorted(set(aa)&set(ra)&set(ad)&set(rd))
    ]


def sanitize_audit_report(report: dict[str,Any]) -> dict[str,Any]:
    """Allowlist-only serialization boundary for the externally downloadable report."""
    top_keys=(
        "status","commit_sha","preregistration","training_rows","dataset_sha256",
        "training_data_sha256","folds","primary_evidence","sum_w_lambda_diagnostic",
        "admission_conclusion","production_promotion","value_betting",
    )
    prereg_keys=(
        "reference_k","tau_team","tau_competition","fold_rule",
        "fold_training_percentages","metrics","home_advantage","half_life_days",
        "bootstrap_replicates","bootstrap_seed","max_iterations",
        "optimizer_tolerance","solver",
    )
    fit_keys=(
        "name","solver","converged","iterations","gradient_norm","fit_error",
        "total_recency_weight","weighted_mean_goals_per_team_match",
        "team_ridge_averaged_objective","competition_ridge_averaged_objective",
        "low_history_test_fixtures","metrics","dispersion_test",
        "dispersion_training_matchups","dispersion_archived_fixtures",
    )
    def pick(source: dict[str,Any], keys: tuple[str,...]) -> dict[str,Any]:
        return {key: source[key] for key in keys if key in source}
    clean={"status":report["status"],"commit_sha":report["commit_sha"]}
    clean["preregistration"]=pick(report["preregistration"],prereg_keys)
    for key in top_keys[3:]:
        if key=="folds":
            folds=[]
            for fold in report["folds"]:
                clean_fits=[pick(fit,fit_keys) for fit in fold["fits"]]
                ratios={}
                for name,value in fold["team_ratio_summaries_archived_vs_reference"].items():
                    if value.get("status")=="NOT_COMPUTED_NON_CONVERGED_FIT":
                        ratios[name]={"status":value["status"]}
                    else:
                        ratios[name]={
                            "ratio_definition":value["ratio_definition"],
                            "attack":value["attack"],"defence":value["defence"],
                            "attack_omitted_near_zero_reference":value["attack_omitted_near_zero_reference"],
                            "defence_omitted_near_zero_reference":value["defence_omitted_near_zero_reference"],
                            "attack_sign_reversals":value["attack_sign_reversals"],
                            "defence_sign_reversals":value["defence_sign_reversals"],
                            "team_effects":value["team_effects"],
                        }
                folds.append({
                    "train_date_range":fold["train_date_range"],
                    "test_date_range":fold["test_date_range"],
                    "train_rows":fold["train_rows"],"test_rows":fold["test_rows"],
                    "cutoff_exclusive_date":fold["cutoff_exclusive"][:10],
                    "home_advantage_climatology":fold["home_advantage_climatology"],
                    "fits":clean_fits,
                    "team_ratio_summaries_archived_vs_reference":ratios,
                    "paired_log_loss_differences_archived_minus_reference":fold["paired_log_loss_differences_archived_minus_reference"],
                })
            clean[key]=folds
        elif key in report:
            clean[key]=report[key]
    return clean


def _home_advantage_climatology(train: list[dict[str,Any]], test: list[dict[str,Any]], cutoff: datetime) -> dict[str,Any]:
    """Training-only recency-weighted 1X2 frequencies, evaluated on this fold."""
    weights=_weights(train,cutoff)
    counts=[0.0,0.0,0.0]
    for row,weight in zip(train,weights):
        hg=int(row["label"]["home_goals"]); ag=int(row["label"]["away_goals"])
        counts[0 if hg>ag else (1 if hg==ag else 2)]+=weight
    total=sum(counts)
    if total<=0:
        raise ValueError("EMPTY_HOME_ADVANTAGE_CLIMATOLOGY")
    probabilities=[value/total for value in counts]
    losses=[]; briers=[]
    for row in test:
        hg=int(row["label"]["home_goals"]); ag=int(row["label"]["away_goals"])
        actual=0 if hg>ag else (1 if hg==ag else 2)
        losses.append(-math.log(max(probabilities[actual],1e-15)))
        briers.append(sum((p-(1.0 if i==actual else 0.0))**2 for i,p in enumerate(probabilities)))
    return {
        "method": "training-only recency-weighted home/draw/away outcome frequencies",
        "training_weighted_outcome_counts": counts,
        "probabilities": {"HOME":probabilities[0],"DRAW":probabilities[1],"AWAY":probabilities[2]},
        "test_metrics": {
            "1X2_log_loss":sum(losses)/len(losses),
            "1X2_multiclass_brier":sum(briers)/len(briers),
            "n":len(test),
        },
    }


def _archived_fixture_dispersion(
    dataset: dict[str,Any], forecast: dict[str,Any], model: Any
) -> dict[str,Any]:
    """Dispersion over the fixed archived forecast fixtures, independent of test fold."""
    rows={
        str(row.get("canonical_fixture_id")):row
        for row in dataset.get("rows",[])
        if row.get("canonical_fixture_id")
    }
    selected=[]
    missing=[]
    for prediction in forecast.get("predictions",[]):
        fixture_id=str(prediction.get("canonical_fixture_id",""))
        row=rows.get(fixture_id)
        if row is None:
            missing.append(fixture_id)
        else:
            selected.append(row)
    result=_dispersion(selected,model) if selected else {"n":0}
    result["expected_archived_fixture_count"]=len(forecast.get("predictions",[]))
    result["matched_archived_fixture_count"]=len(selected)
    result["missing_archived_fixture_count"]=len(missing)
    return result


def _bootstrap(diffs: list[tuple[str,float]], seed: int) -> dict[str,float]:
    # Paired date-block bootstrap: sample kickoff-date clusters with replacement.
    import random
    groups: dict[str,list[float]]={}
    for date,value in diffs: groups.setdefault(date,[]).append(value)
    dates=sorted(groups)
    if len(dates)<2: return {"mean":sum(v for _,v in diffs)/len(diffs),"ci95_low":float("nan"),"ci95_high":float("nan"),"date_blocks":len(dates)}
    rng=random.Random(seed); samples=[]
    for _ in range(BOOTSTRAP_REPLICATES):
        chosen=[rng.choice(dates) for _ in dates]
        values=[v for date in chosen for v in groups[date]]
        samples.append(sum(values)/len(values))
    samples.sort()
    return {"mean":sum(v for _,v in diffs)/len(diffs),"ci95_low":samples[int(.025*len(samples))],"ci95_high":samples[int(.975*len(samples))-1],"date_blocks":len(dates)}


def run_audit(dataset: dict[str,Any], forecast: dict[str,Any], *, commit_sha: str) -> dict[str,Any]:
    rows=dataset["training_only_rows"]
    if dataset.get("dataset_sha256") != EXPECTED_DATASET_SHA: raise ValueError("DATASET_SHA_MISMATCH")
    from app.research.shadow_model_audit import training_data_sha256
    if training_data_sha256(rows) != EXPECTED_TRAINING_SHA: raise ValueError("TRAINING_SHA_MISMATCH")
    if len(rows)!=996: raise ValueError("TRAINING_ROW_COUNT_MISMATCH")
    dates=sorted({_dt(r["kickoff_at"]).date().isoformat() for r in rows})
    folds=[]
    for pct in (60,70,80,90):
        cut=max(1,min(len(dates)-1,math.floor(len(dates)*pct/100)))
        test_end=min(len(dates),cut+max(1,math.ceil(len(dates)*.10)))
        train_dates=set(dates[:cut]); test_dates=set(dates[cut:test_end])
        train=[r for r in rows if _dt(r["kickoff_at"]).date().isoformat() in train_dates]
        test=[r for r in rows if _dt(r["kickoff_at"]).date().isoformat() in test_dates]
        if not train or not test: raise ValueError(f"EMPTY_FOLD_{pct}")
        cutoff=min(_dt(r["kickoff_at"]) for r in test)
        if any(_dt(r["kickoff_at"])>=cutoff for r in train): raise ValueError("FOLD_LEAKAGE")
        fits=[]
        configs=[("archived",None,True)]+[(f"reference_k_{k}",k,False) for k in REFERENCE_K]
        counts={}
        for r in train:
            counts[str(r["home_team_id"])]=counts.get(str(r["home_team_id"]),0)+1
            counts[str(r["away_team_id"])]=counts.get(str(r["away_team_id"]),0)+1
        low=sum(1 for r in test if counts.get(str(r["home_team_id"]),0)<5 or counts.get(str(r["away_team_id"]),0)<5)
        for name,k,is_archived in configs:
            fit=_fit_for_audit(train,cutoff,k=k,archived=is_archived)
            model=fit["model"]
            item={"name":name,"solver":fit["solver"],"converged":fit["converged"],"iterations":fit["iterations"],"gradient_norm":fit["gradient_norm"],"fit_error":fit["error"],"total_recency_weight":fit["total_recency_weight"],"weighted_mean_goals_per_team_match":fit["weighted_mean_goals_per_team_match"],"team_ridge_averaged_objective":fit["team_ridge_averaged_objective"],"competition_ridge_averaged_objective":fit["competition_ridge_averaged_objective"],"low_history_test_fixtures":low,"model":model}
            if model is not None:
                item["metrics"]=_metrics(test,model)
                item["dispersion_test"]=_dispersion(test,model)
                item["dispersion_training_matchups"]=_dispersion(train,model)
                item["dispersion_archived_fixtures"]=_archived_fixture_dispersion(
                    dataset,forecast,model
                )
            fits.append(item)
        archived=fits[0]
        comparisons={}
        for ref in fits[1:]:
            if archived["model"] is None or ref["model"] is None:
                comparisons[ref["name"]]={"status":"NOT_COMPUTED_NON_CONVERGED_FIT"}
                continue
            diffs=[]
            for r in test:
                pa=_probabilities(archived["model"].predict(str(r["home_team_id"]),str(r["away_team_id"]),str(r["competition_id"])).home_lambda,archived["model"].predict(str(r["home_team_id"]),str(r["away_team_id"]),str(r["competition_id"])).away_lambda)
                pr=_probabilities(ref["model"].predict(str(r["home_team_id"]),str(r["away_team_id"]),str(r["competition_id"])).home_lambda,ref["model"].predict(str(r["home_team_id"]),str(r["away_team_id"]),str(r["competition_id"])).away_lambda)
                hg,ag=int(r["label"]["home_goals"]),int(r["label"]["away_goals"]); actual=0 if hg>ag else (1 if hg==ag else 2)
                diffs.append((_dt(r["kickoff_at"]).date().isoformat(),-math.log(max(pa[actual],1e-15))+math.log(max(pr[actual],1e-15))))
            comparisons[ref["name"]]={
                "status":"COMPUTED",
                **_bootstrap(diffs,BOOTSTRAP_SEED+pct),
            }
        ratios={}
        for ref in fits[1:]:
            if archived["model"] is None or ref["model"] is None:
                ratios[ref["name"]]={"status":"NOT_COMPUTED_NON_CONVERGED_FIT"}
            else:
                ratios[ref["name"]]=_centered_team_ratio_summary(
                    archived["model"],ref["model"]
                )
                ratios[ref["name"]]["team_effects"]=_centered_team_effects(
                    archived["model"],ref["model"]
                )
        public_fits=[{key:value for key,value in f.items() if key!="model"} for f in fits]
        folds.append({
            "train_date_range":[dates[0],dates[cut-1]],
            "test_date_range":[dates[cut],dates[test_end-1]],
            "train_rows":len(train),
            "test_rows":len(test),
            "cutoff_exclusive":cutoff.isoformat(),
            "home_advantage_climatology":_home_advantage_climatology(train,test,cutoff),
            "fits":public_fits,
            "team_ratio_summaries_archived_vs_reference":ratios,
            "paired_log_loss_differences_archived_minus_reference":comparisons,
        })
    return {"status":"DIAGNOSTIC_ONLY","commit_sha":commit_sha,"preregistration":{"reference_k":list(REFERENCE_K),"tau_team":"k*mu","tau_competition":"k*2*mu","fold_rule":FOLD_RULE,"fold_training_percentages":[60,70,80,90],"metrics":list(METRICS),"home_advantage":HOME_ADVANTAGE_TREATMENT,"half_life_days":365,"bootstrap_replicates":BOOTSTRAP_REPLICATES,"bootstrap_seed":BOOTSTRAP_SEED,"max_iterations":MAX_ITERATIONS,"optimizer_tolerance":OPTIMIZER_TOLERANCE,"solver":"L-BFGS with Armijo backtracking"},"training_rows":len(rows),"dataset_sha256":dataset["dataset_sha256"],"training_data_sha256":training_data_sha256(rows),"folds":folds,"primary_evidence":"fit-to-fit comparison; paired date-block bootstrap log-loss differences","sum_w_lambda_diagnostic":"first-order approximation only; attack and defence jointly estimated","admission_conclusion":"NONE: corpus is not point-in-time certified","production_promotion":"LOCKED","value_betting":"LOCKED"}
