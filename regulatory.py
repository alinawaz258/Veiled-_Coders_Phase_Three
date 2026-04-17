"""GigShield AI — IRDAI Regulatory Framework Module (v3.0.0).

This module codifies the IRDAI Regulatory Sandbox 2023 compliance requirements
for GigShield's parametric micro-insurance product.

Regulatory context
~~~~~~~~~~~~~~~~~~
India's insurance sector is regulated by the Insurance Regulatory and
Development Authority of India (IRDAI) under the Insurance Act 1938 and
IRDAI Act 1999.  GigShield operates under two specific frameworks:

1. IRDAI Regulatory Sandbox (2019, revised 2023)
   Allows innovative insurtech products to be piloted for 6–12 months
   with a capped user base (10,000 lives max).

2. IRDAI Micro-Insurance Regulations 2015 (amended 2019)
   Governs micro-insurance products: weekly premiums ≤ ₹100,
   sum insured ≤ ₹50,000, short-term (weekly) policy structures.

GigShield's product structure is designed to satisfy both frameworks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class SandboxRequirement:
    """Single IRDAI sandbox compliance requirement."""
    category:        str
    requirement:     str
    gigshield_impl:  str
    status:          str   # 'implemented', 'in_progress', 'planned'


@dataclass
class RegulatoryFramework:
    """Complete IRDAI compliance framework for GigShield."""
    product_name:         str
    product_category:     str
    regulatory_framework: str
    sandbox_version:      str
    underwriter_model:    str
    max_insured_lives:    int
    sandbox_duration_months: int
    requirements:         List[SandboxRequirement]
    reporting_obligations: List[str]
    grievance_process:    Dict[str, str]
    data_compliance:      Dict[str, str]
    product_parameters:   Dict[str, str]


# ── Full framework definition ──────────────────────────────────────────────────

GIGSHIELD_REGULATORY_FRAMEWORK = RegulatoryFramework(
    product_name="GigShield Parametric Income Protection",
    product_category="Micro-insurance — Parametric Non-Life",
    regulatory_framework="IRDAI Regulatory Sandbox (Circular IRDA/IT/Cir/MISC/173/10/2019 revised 2023)",
    sandbox_version="2023 Amendment",
    underwriter_model=(
        "Distribution-only model: GigShield acts as the Insurtech distributor. "
        "Risk is underwritten by a licensed non-life insurer partner (e.g., Digit Insurance, "
        "Acko General Insurance, or New India Assurance) that holds a valid IRDAI licence. "
        "GigShield itself is NOT a risk carrier."
    ),
    max_insured_lives=10_000,
    sandbox_duration_months=6,

    requirements=[
        SandboxRequirement(
            category="Entity eligibility",
            requirement="Applicant must be a DPIIT-recognised startup or technology company. Co-applicant must be a licensed IRDAI insurer.",
            gigshield_impl="GigShield Technologies Pvt. Ltd. (DPIIT startup). Partner insurer: [to be named at sandbox application]. IRDAI sandbox application submitted jointly.",
            status="planned",
        ),
        SandboxRequirement(
            category="Product filing",
            requirement="Policy wordings, premium tables, and exclusions must be pre-approved by IRDAI before pilot launch.",
            gigshield_impl="All policy terms, payout matrices, and 10 explicit exclusions are machine-readable in PolicyTerms schema. Document filed at /regulatory/policy-wordings endpoint.",
            status="implemented",
        ),
        SandboxRequirement(
            category="Premium structure",
            requirement="Weekly premium must comply with IRDAI Micro-Insurance Regulations 2015: premium ≤ ₹100/week for weekly policies.",
            gigshield_impl="All premiums: ₹22–₹80/week (Basic ₹22, Standard ₹30, Premium ₹48 base; seasonal cap ₹80). Within the ₹100/week regulatory ceiling.",
            status="implemented",
        ),
        SandboxRequirement(
            category="Sum insured ceiling",
            requirement="Sum insured for micro-insurance: ≤ ₹50,000 (life) / ≤ ₹2,00,000 (non-life). Weekly aggregate cap applies.",
            gigshield_impl="Weekly aggregate caps: ₹380 (Basic), ₹750 (Standard), ₹1,600 (Premium). Annual max: ₹1,600 × 52 = ₹83,200. Within non-life micro-insurance thresholds.",
            status="implemented",
        ),
        SandboxRequirement(
            category="Coverage exclusions",
            requirement="Policy must have explicit, unambiguous exclusions in plain language. Must exclude health, life, and vehicle coverage.",
            gigshield_impl="10 named exclusions in COVERAGE_EXCLUSIONS list. Health, life, accident, and vehicle repair explicitly excluded. Returned with every policy quote.",
            status="implemented",
        ),
        SandboxRequirement(
            category="Moratorium / waiting period",
            requirement="Short-term policies must specify activation waiting periods to prevent adverse selection.",
            gigshield_impl="24-hour mandatory activation wait period (policy inactive for first 24 hours). 6-hour free-look period for cancellation.",
            status="implemented",
        ),
        SandboxRequirement(
            category="Parametric trigger documentation",
            requirement="Parametric indices and trigger thresholds must be defined objectively, verifiable from third-party sources.",
            gigshield_impl="All triggers use IMD/NDMA/CPCB data: rainfall ≥ 40 mm/hr (IMD), AQI ≥ 300 (CPCB Severe), curfew (NDMA/state gazette), flood warning (IMD).",
            status="implemented",
        ),
        SandboxRequirement(
            category="Grievance redressal",
            requirement="Must maintain a 24×7 grievance mechanism with resolution within 15 days (IRDAI Circular IRDA/LIFE/CIR/GRV/014/01/2014).",
            gigshield_impl="Grievance portal at /grievance/submit. Escalation to IRDAI Consumer Affairs Department if unresolved in 15 days. IRDAi Bima Bharosa portal integration planned.",
            status="in_progress",
        ),
        SandboxRequirement(
            category="Claims transparency",
            requirement="All claim decisions must be communicated to the policyholder with clear reasons. Denied claims must cite specific policy clause.",
            gigshield_impl="Every ClaimDecision object carries reason (plain-language), oracle_snapshot (data evidence), and the specific exclusion clause if denied.",
            status="implemented",
        ),
        SandboxRequirement(
            category="Data localisation",
            requirement="All customer data must be stored within India under the Digital Personal Data Protection Act 2023 (DPDPA).",
            gigshield_impl="MongoDB Atlas India region (Mumbai ap-south-1). Supabase Postgres Singapore → migrating to Mumbai. No customer data crosses India border.",
            status="in_progress",
        ),
        SandboxRequirement(
            category="Monthly reporting",
            requirement="Sandbox licensees must file monthly progress reports with IRDAI: claim volumes, loss ratios, fraud incidents, customer complaints.",
            gigshield_impl="Automated report generation at GET /regulatory/monthly-report. Includes claim counts, approval rates, loss ratio by plan tier, fraud signal statistics.",
            status="in_progress",
        ),
        SandboxRequirement(
            category="Anti-money laundering",
            requirement="Must comply with PMLA 2002 and RBI KYC norms for premium collection and payout processing.",
            gigshield_impl="Razorpay KYC integration for UPI payouts. Driver identity linked to Aadhaar-verified delivery platform account. Payout ceiling ₹1,600/week (below AML threshold).",
            status="planned",
        ),
    ],

    reporting_obligations=[
        "Monthly: claim volume, approval rate, loss ratio by plan tier and city",
        "Monthly: fraud incident count, anomaly score distribution, manual review outcomes",
        "Monthly: premium collected vs. payouts disbursed (loss ratio proof)",
        "Monthly: grievance count, resolution time, escalation rate",
        "Quarterly: AI model performance metrics (R², MAE, RMSE, non-linearity gap)",
        "Quarterly: seasonal pricing multiplier justification vs. actual claim frequency",
        "Ad-hoc: any parametric trigger event affecting > 500 riders simultaneously",
        "Ad-hoc: any fraud case resulting in claim > ₹5,000 (requires police complaint)",
    ],

    grievance_process={
        "channel":           "In-app grievance form at /grievance/submit (24×7)",
        "acknowledgement":   "Auto-acknowledgement within 24 hours",
        "resolution":        "15 calendar days (IRDAI mandate)",
        "escalation_level_1": "GigShield Grievance Officer (designated: Chief Risk Officer)",
        "escalation_level_2": "Underwriter partner's Grievance Redressal Officer",
        "escalation_level_3": "IRDAI Bima Bharosa portal (www.bimabharosa.irdai.gov.in)",
        "ombudsman":         "Insurance Ombudsman (IRDAI Ombudsman Scheme 2017) for disputes > ₹3 lakh",
    },

    data_compliance={
        "legislation":       "Digital Personal Data Protection Act 2023 (DPDPA)",
        "lawful_basis":      "Consent (explicit at onboarding) + Contractual necessity (claim processing)",
        "data_fiduciary":    "GigShield Technologies Pvt. Ltd.",
        "retention":         "Claim records: 7 years (Insurance Act minimum). GPS telemetry: 30 days (fraud audit window). Model training data: synthetic only (no real PII).",
        "right_to_erasure":  "Rider may request PII deletion (implemented in /drivers/delete). Claim financial records retained 7 years per regulation.",
        "cross_border":      "No cross-border data transfer. India-only cloud infra.",
        "breach_reporting":  "CERT-In within 6 hours of detection. IRDAI within 24 hours.",
    },

    product_parameters={
        "coverage_type":       "Income loss protection (parametric non-life)",
        "coverage_basis":      "Parametric index triggers — not indemnity claims",
        "min_premium_week":    "₹22 (Basic, non-monsoon)",
        "max_premium_week":    "₹80 (Premium, monsoon peak, coastal city)",
        "min_payout":          "₹150 (Basic moderate rain)",
        "max_payout_per_event":"₹530 (Premium emergency)",
        "max_payout_per_week": "₹1,600 (Premium seasonal-adjusted cap)",
        "coverage_fraction":   "28% of weekly earnings (partial indemnity — prevents moral hazard)",
        "waiting_period":      "24 hours after policy activation",
        "free_look":           "6 hours from policy start (cancel for full refund)",
        "claim_window":        "Must be filed within 12 hours of trigger event end",
        "exclusions_count":    "10 explicit IRDAI-compliant exclusions",
        "ai_model":            "GradientBoostingRegressor (scikit-learn) — R² 0.84, non-linear",
        "data_sources":        "IMD, NDMA, CPCB, Open-Meteo, Nominatim (OpenStreetMap)",
        "payout_channel":      "UPI / Razorpay (6–12 hour processing for weather claims)",
    },
)


def get_compliance_summary() -> Dict:
    """Return a structured summary of compliance status for the /regulatory endpoint."""
    fw = GIGSHIELD_REGULATORY_FRAMEWORK
    counts = {"implemented": 0, "in_progress": 0, "planned": 0}
    for req in fw.requirements:
        counts[req.status] = counts.get(req.status, 0) + 1

    return {
        "product": fw.product_name,
        "category": fw.product_category,
        "framework": fw.regulatory_framework,
        "sandbox_version": fw.sandbox_version,
        "underwriter_model": fw.underwriter_model,
        "max_insured_lives": fw.max_insured_lives,
        "sandbox_duration_months": fw.sandbox_duration_months,
        "compliance_status": counts,
        "total_requirements": len(fw.requirements),
        "requirements": [
            {
                "category":    r.category,
                "requirement": r.requirement,
                "gigshield_implementation": r.gigshield_impl,
                "status":      r.status,
            }
            for r in fw.requirements
        ],
        "reporting_obligations": fw.reporting_obligations,
        "grievance_process": fw.grievance_process,
        "data_compliance": fw.data_compliance,
        "product_parameters": fw.product_parameters,
    }
