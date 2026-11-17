#!/usr/bin/env python3
"""Regenerate job_exp.yml (BaseExp to level 999, JobExp to level 80) and
statpoint.yml (to level 999), per Aethera's level cap bump.

Base EXP: levels 1-999 split into 10 tiers of up to 100 levels. Tier 0
(1-100) keeps the vanilla per-level curve as-is (defines the baseline
unit "X"). Each following tier's total EXP doubles (tier t costs X*2^t),
reusing the same per-level shape scaled to hit that total.

Job EXP: each existing job group's own curve is fit to a power law
a*L^b (least squares on log-log of its real data, dropping the last
entry which is a throwaway/sentinel value in every group) and
re-evaluated for levels 1-80, keeping each group's distinct pacing
instead of unifying them.

Statpoint: levels 1-200 already follow the real official formula
(points_needed(L) = floor((L+15)/5)); levels 201-275 in the current
file are an artificial flatline padding. Continue the real formula
through level 999 instead.
"""
import math
import yaml

JOB_EXP_PATH = "db/pre-re/job_exp.yml"
STATPOINT_PATH = "db/pre-re/statpoint.yml"

MAX_BASE_LEVEL = 999
MAX_JOB_LEVEL = 80


def gen_base_exp(rebirth_shape99):
    """rebirth_shape99: 99 ints, the *rebirth* (trans/_High) classes'
    real vanilla cost to go from level i to i+1 (i=1..99) -- used as the
    baseline per the user's call: anchor on the real rebirth 1-99 table,
    not an arbitrary time target.

    exp(L) = C * r^L, with r = 2**(1/100). Over any 100-level span, r^100
    == 2, so the sum over levels [100k+1, 100k+100] is automatically
    exactly double the sum over the previous 100-level span, for every
    k, with no reset at the boundaries -- unlike reusing the same
    per-level shape every tier, which makes level 101 cheap again right
    after level 100's peak (tried first; the fix is a constant per-level
    growth rate instead of a repeating shape).

    The real table's last entry (level 99) is a flat 99,999,999
    sentinel (same "cap reached" placeholder convention used
    everywhere in this file, e.g. Novice/Baby's job exp at level 10) --
    replaced with one more step at the level 98->99 growth rate before
    summing, so that placeholder doesn't by itself inflate the baseline.
    """
    real = list(rebirth_shape99[:-1])  # levels 1-98, real values
    real.append(round(real[-1] * (real[-1] / real[-2])))  # level 99, continuing the real trend
    baseline = sum(real) + real[-1]  # X: total for levels 1-100 (level 100 ~= level 99)

    r = 2 ** (1 / 100)
    geometric_sum_100 = r * (r ** 100 - 1) / (r - 1)  # sum_{L=1}^{100} r^L
    c = baseline / geometric_sum_100

    result = {}
    for level in range(1, MAX_BASE_LEVEL + 1):
        result[level] = max(1, round(c * (r ** level)))
    return result


def fit_power_law(points):
    """points: list of (level, exp). Returns (a, b) for exp = a * level^b."""
    xs = [math.log(l) for l, _ in points]
    ys = [math.log(e) for _, e in points]
    n = len(points)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    b = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    ln_a = (sy - b * sx) / n
    return math.exp(ln_a), b


def gen_job_exp(existing):
    """existing: list of {'Level':..,'Exp':..} dicts (vanilla curve, any length).
    Drops the last entry (sentinel/unused) before fitting."""
    pts = [(e["Level"], e["Exp"]) for e in existing[:-1]]
    a, b = fit_power_law(pts)
    result = {}
    for level in range(1, MAX_JOB_LEVEL + 1):
        result[level] = max(1, round(a * (level ** b)))
    return result


def main():
    with open(JOB_EXP_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rebirth_group = next(g for g in data["Body"] if "Novice_High" in g.get("Jobs", {}))
    base_shape = [e["Exp"] for e in rebirth_group["BaseExp"]]
    assert len(base_shape) == 99, len(base_shape)
    new_base_exp = gen_base_exp(base_shape)
    base_exp_list = [{"Level": lvl, "Exp": new_base_exp[lvl]} for lvl in sorted(new_base_exp)]

    for group in data["Body"]:
        if "BaseExp" in group:
            group["MaxBaseLevel"] = MAX_BASE_LEVEL
            group["BaseExp"] = base_exp_list
        if "JobExp" in group:
            new_job_exp = gen_job_exp(group["JobExp"])
            group["MaxJobLevel"] = MAX_JOB_LEVEL
            group["JobExp"] = [{"Level": lvl, "Exp": new_job_exp[lvl]} for lvl in sorted(new_job_exp)]

    write_job_exp_yml(data)
    write_statpoint_yml()


def write_job_exp_yml(data):
    header = """# This file is a part of rAthena.
#   Copyright(C) 2021 rAthena Development Team
#   https://rathena.org - https://github.com/rathena
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###########################################################################
# Job Experience Database - Aethera: base level cap 999, job level cap 80
###########################################################################
#
# BaseExp: levels 1-100 keep the vanilla per-level curve unchanged (the
# baseline unit "X"). Every following 100-level tier costs double the
# previous tier's total (100-200 = 2X, 200-300 = 4X, ... 900-999 = 512X),
# reusing the same per-level shape scaled to hit that total.
#
# JobExp: each group's own vanilla curve fit to a power law and
# re-evaluated out to level 80, keeping each job's original relative
# pacing instead of unifying every class onto one curve.
#
# Generated by gen_level_tables.py from the stock db/pre-re/job_exp.yml -
# do not hand-edit, regenerate instead if the vanilla base shifts.
###########################################################################

"""
    lines = [header]
    lines.append("Header:\n")
    lines.append(f"  Type: {data['Header']['Type']}\n")
    lines.append(f"  Version: {data['Header']['Version']}\n\n")
    lines.append("Body:\n")
    for group in data["Body"]:
        lines.append("  - Jobs:\n")
        for job, v in group["Jobs"].items():
            lines.append(f"      {job}: {str(v).lower()}\n")
        if "MaxBaseLevel" in group:
            lines.append(f"    MaxBaseLevel: {group['MaxBaseLevel']}\n")
            lines.append("    BaseExp:\n")
            for e in group["BaseExp"]:
                lines.append(f"      - Level: {e['Level']}\n")
                lines.append(f"        Exp: {e['Exp']}\n")
        if "MaxJobLevel" in group:
            lines.append(f"    MaxJobLevel: {group['MaxJobLevel']}\n")
            lines.append("    JobExp:\n")
            for e in group["JobExp"]:
                lines.append(f"      - Level: {e['Level']}\n")
                lines.append(f"        Exp: {e['Exp']}\n")
    with open(JOB_EXP_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Wrote {len(data['Body'])} groups to {JOB_EXP_PATH}")


def write_statpoint_yml():
    # Real official formula, confirmed against the existing table's
    # levels 1-200 (which already follow it exactly): points needed to
    # go from level L to L+1 is floor((L+15)/5). Levels 201-275 in the
    # stock file are an artificial flatline padding -- continue the real
    # formula through 999 instead.
    points = {1: 48}
    for level in range(1, MAX_BASE_LEVEL):
        points[level + 1] = points[level] + (level + 15) // 5

    header = """# This file is a part of rAthena.
#   Copyright(C) 2021 rAthena Development Team
#   https://rathena.org - https://github.com/rathena
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###########################################################################
# Statpoint Database - Aethera: extended to level 999
###########################################################################
#
# - Level             BaseLevel required.
#   Points            Total status points given from BaseLevel 1 to 'Level'.
#
# Levels 1-200 are the stock values (official formula). The stock file
# artificially flatlined from level 201 to its old 275 cap instead of
# continuing the formula; this file continues it for real, through 999:
# points_needed(L) = floor((L+15)/5).
# Generated by gen_level_tables.py -- do not hand-edit, regenerate instead.
###########################################################################

Header:
  Type: STATPOINT_DB
  Version: 2

Body:
"""
    lines = [header]
    for level in range(1, MAX_BASE_LEVEL + 1):
        lines.append(f"  - Level: {level}\n")
        lines.append(f"    Points: {points[level]}\n")
    with open(STATPOINT_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Wrote {MAX_BASE_LEVEL} entries to {STATPOINT_PATH}")


if __name__ == "__main__":
    main()
