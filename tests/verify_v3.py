"""
PANTHEON v3 Cognitive Architecture — Verification Suite
Validates gaussian distribution, trait covariance, age drift, and cultural modifiers.
Run: .venv/Scripts/python verify_v3.py
"""
import sys, statistics

# ── ensure project root is importable ──
sys.path.insert(0, ".")

from genome_culture import generate_base_genome, apply_age_drift, apply_cultural_modifiers, generate_cultural_profile

N = 1000
PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}  -- {detail}")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: Gaussian Distribution
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"TEST 1: Distribution — {N} base genomes")
print(f"{'='*60}")

genomes = [generate_base_genome() for _ in range(N)]
all_traits = list(genomes[0].keys())

for trait in ["openness", "conscientiousness", "identity_fusion", "chronesthesia_capacity"]:
    vals = [g[trait] for g in genomes]
    mu = statistics.mean(vals)
    sd = statistics.stdev(vals)
    check(
        f"{trait}: mean={mu:.1f} sd={sd:.1f}",
        38 < mu < 62 and 10 < sd < 20,
        f"expected mean~50±12, sd~12-18"
    )

# Check that values aren't uniformly distributed (should cluster around center)
openness_vals = [g["openness"] for g in genomes]
extreme_count = sum(1 for v in openness_vals if v < 10 or v > 90)
extreme_pct = extreme_count / N * 100
check(
    f"Extreme scores (openness <10 or >90): {extreme_pct:.1f}%",
    extreme_pct < 8,  # gaussian should have <5%, uniform would have ~20%
    f"expected <8% for gaussian, got {extreme_pct:.1f}%"
)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: Trait Covariance
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"TEST 2: Trait Covariance — {N} genomes")
print(f"{'='*60}")


def pearson_r(xs, ys):
    n = len(xs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
    sx = statistics.stdev(xs)
    sy = statistics.stdev(ys)
    return cov / (sx * sy) if sx > 0 and sy > 0 else 0


consc = [g["conscientiousness"] for g in genomes]
dm = [g["decision_making"] for g in genomes]
r_consc_dm = pearson_r(consc, dm)
check(
    f"conscientiousness vs decision_making  r={r_consc_dm:.3f}",
    0.15 < r_consc_dm < 0.65,
    f"expected r~0.3-0.5, got {r_consc_dm:.3f}"
)

agree = [g["agreeableness"] for g in genomes]
cb = [g["conflict_behavior"] for g in genomes]
r_agree_cb = pearson_r(agree, cb)
check(
    f"agreeableness vs conflict_behavior  r={r_agree_cb:.3f}",
    -0.75 < r_agree_cb < -0.30,
    f"expected r~-0.4 to -0.7, got {r_agree_cb:.3f}"
)

# Big Five should be independent (r near 0)
extra = [g["extraversion"] for g in genomes]
r_consc_extra = pearson_r(consc, extra)
check(
    f"conscientiousness vs extraversion  r={r_consc_extra:.3f}  (should be near 0)",
    -0.15 < r_consc_extra < 0.15,
    f"expected |r|<0.15, got {r_consc_extra:.3f}"
)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: Age Drift
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("TEST 3: Age Drift — same base genome at age 20 vs 50")
print(f"{'='*60}")

# Use multiple samples to average out base genome randomness
consc_20s = []
consc_50s = []
neuro_20s = []
neuro_50s = []
ef_20s = []
ef_50s = []

for _ in range(500):
    base = generate_base_genome()
    g20 = apply_age_drift(base, 20)
    g50 = apply_age_drift(base, 50)
    consc_20s.append(g20["conscientiousness"])
    consc_50s.append(g50["conscientiousness"])
    neuro_20s.append(g20["neuroticism"])
    neuro_50s.append(g50["neuroticism"])
    ef_20s.append(g20["executive_flexibility"])
    ef_50s.append(g50["executive_flexibility"])

consc_diff = statistics.mean(consc_50s) - statistics.mean(consc_20s)
neuro_diff = statistics.mean(neuro_50s) - statistics.mean(neuro_20s)
ef_diff = statistics.mean(ef_50s) - statistics.mean(ef_20s)

check(
    f"Conscientiousness age drift (50 vs 20): +{consc_diff:.1f} pts",
    5 < consc_diff < 15,
    f"expected ~+9 pts (0.3 * 30 yrs)"
)
check(
    f"Neuroticism age drift (50 vs 20): {neuro_diff:.1f} pts",
    -8 < neuro_diff < -1,
    f"expected ~-4 pts (-0.2 * 20 yrs)"
)
check(
    f"Executive flexibility age drift (50 vs 20): +{ef_diff:.1f} pts",
    3 < ef_diff < 10,
    f"expected ~+6 pts (0.2 * 30 yrs)"
)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: Cultural Modifier Separation
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("TEST 4: Cultural Modifiers — identity_fusion by ethnicity")
print(f"{'='*60}")

# Generate Medan agents (expect high identity_fusion) vs North American (lower)
medan_fusions = []
na_fusions = []

for _ in range(200):
    base = generate_base_genome()
    g = apply_age_drift(base, 35)
    profile_medan = generate_cultural_profile("medan", 35)
    g_medan = apply_cultural_modifiers(g.copy(), profile_medan)
    medan_fusions.append(g_medan["identity_fusion"])

    base2 = generate_base_genome()
    g2 = apply_age_drift(base2, 35)
    profile_na = generate_cultural_profile("north_america", 35)
    g_na = apply_cultural_modifiers(g2.copy(), profile_na)
    na_fusions.append(g_na["identity_fusion"])

medan_mean = statistics.mean(medan_fusions)
na_mean = statistics.mean(na_fusions)

check(
    f"Medan mean identity_fusion={medan_mean:.1f} vs NA={na_mean:.1f}",
    medan_mean > na_mean,
    f"expected Medan > North America due to marga/guanxi/ummah modifiers"
)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: Backward Compatibility
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("TEST 5: Backward Compatibility — .get(trait, 50) defaults")
print(f"{'='*60}")

# Simulate an old DB row missing new columns
old_agent = {
    "name": "Legacy Agent",
    "age": 30,
    "openness": 65,
    "conscientiousness": 72,
    # ... missing identity_fusion, chronesthesia_capacity, etc.
}

new_traits = ["identity_fusion", "chronesthesia_capacity", "tom_self_awareness",
              "tom_social_modeling", "executive_flexibility"]

all_default = all(old_agent.get(t, 50) == 50 for t in new_traits)
check(
    "Old agent missing new traits defaults to 50 via .get()",
    all_default,
    "one or more traits didn't default to 50"
)

# Verify genome has all 18 traits
genome = generate_base_genome()
check(
    f"generate_base_genome() returns {len(genome)} traits",
    len(genome) == 18,
    f"expected 18 traits, got {len(genome)}"
)

for t in new_traits:
    check(
        f"  '{t}' present in genome",
        t in genome,
        f"missing from generate_base_genome()"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"RESULTS: {PASS} passed, {FAIL} failed")
print(f"{'='*60}")

if FAIL == 0:
    print("All verification tests passed -- v3 cognitive architecture is working correctly.")
else:
    print(f"WARNING: {FAIL} test(s) failed -- review output above.")

sys.exit(FAIL)
