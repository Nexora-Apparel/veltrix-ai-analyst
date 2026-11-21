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
    ordered=sorted(x for x,_ in values)
    if not ordered: return {"median":None,"q1":None,"q3":None,"weighted_median":None}
    def quantile(v: list[float],q:float)->float:
        z=(len(v)-1)*q;lo=int(z);hi=min(lo+1,len(v)-1);return v[lo]+(v[hi]-v[lo])*(z-lo)
    pairs=sorted(values); total=sum(w for _,w in pairs); acc=0; wm=pairs[-1][0]
    for value,weight in pairs:
        acc+=weight
        if acc>=total/2: wm=value;break
    return {"median":median(ordered),"q1":quantile(ordered,.25),"q3":quantile(ordered,.75),"weighted_median":wm}


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
        configs=[("archived",.5,.5)]+[(f"reference_k_{k}",k,k*2) for k in REFERENCE_K]
        for name,tr,cr in configs:
            model=fit_hierarchical_poisson([_result(r) for r in train],as_of=cutoff,half_life_days=365,team_ridge=tr,competition_ridge=cr)
            predicted=[]
            low=0
            counts={}
            for r in train:
                counts[str(r["home_team_id"])]=counts.get(str(r["home_team_id"]),0)+1
                counts[str(r["away_team_id"])]=counts.get(str(r["away_team_id"]),0)+1
            for r in test:
                if counts.get(str(r["home_team_id"]),0)<5 or counts.get(str(r["away_team_id"]),0)<5: low+=1
                predicted.append(r)
            fits.append({"name":name,"converged":model.optimizer_converged,"iterations":model.optimizer_iterations,"gradient_norm":model.optimizer_gradient_norm,"metrics":_metrics(test,model),"dispersion_test":_dispersion(test,model),"dispersion_training_matchups":_dispersion(train,model),"low_history_test_fixtures":low,"model":model})
        archived=fits[0]
        comparisons={}
        for ref in fits[1:]:
            diffs=[]
            for r in test:
                pa=_probabilities(archived["model"].predict(str(r["home_team_id"]),str(r["away_team_id"]),str(r["competition_id"])).home_lambda,archived["model"].predict(str(r["home_team_id"]),str(r["away_team_id"]),str(r["competition_id"])).away_lambda)
                pr=_probabilities(ref["model"].predict(str(r["home_team_id"]),str(r["away_team_id"]),str(r["competition_id"])).home_lambda,ref["model"].predict(str(r["home_team_id"]),str(r["away_team_id"]),str(r["competition_id"])).away_lambda)
                hg,ag=int(r["label"]["home_goals"]),int(r["label"]["away_goals"]); actual=0 if hg>ag else (1 if hg==ag else 2)
                diffs.append((_dt(r["kickoff_at"]).date().isoformat(),-math.log(max(pa[actual],1e-15))+math.log(max(pr[actual],1e-15))))
            comparisons[ref["name"]]=_bootstrap(diffs,BOOTSTRAP_SEED+pct)
        public_fits=[{k:v for k,v in f.items() if k!="model"} for f in fits]
        folds.append({"train_date_range":[dates[0],dates[cut-1]],"test_date_range":[dates[cut],dates[test_end-1]],"train_rows":len(train),"test_rows":len(test),"cutoff_exclusive":cutoff.isoformat(),"fits":public_fits,"paired_log_loss_differences_archived_minus_reference":comparisons})
    return {"status":"DIAGNOSTIC_ONLY","commit_sha":commit_sha,"preregistration":{"reference_k":list(REFERENCE_K),"tau_team":"k*mu","tau_competition":"k*2*mu","fold_rule":FOLD_RULE,"fold_training_percentages":[60,70,80,90],"metrics":list(METRICS),"home_advantage":HOME_ADVANTAGE_TREATMENT,"half_life_days":365,"bootstrap_replicates":BOOTSTRAP_REPLICATES,"bootstrap_seed":BOOTSTRAP_SEED},"training_rows":len(rows),"dataset_sha256":dataset["dataset_sha256"],"training_data_sha256":training_data_sha256(rows),"folds":folds,"primary_evidence":"fit-to-fit comparison; paired date-block bootstrap log-loss differences","sum_w_lambda_diagnostic":"first-order approximation only; attack and defence jointly estimated","admission_conclusion":"NONE: corpus is not point-in-time certified","production_promotion":"LOCKED","value_betting":"LOCKED"}
