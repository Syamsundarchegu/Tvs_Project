# NOT_AVAILABLE = "Not Available"

# METADATA_SCHEMA = {
#     "business_area": {
#         "description": "Business area the document belongs to within TVS Capital (e.g. Portfolio).",
#         "examples": ["Portfolio"],
#     },
#     "entity_type": {
#         "description": "Type of entity the document is about.",
#         "examples": ["Company"],
#     },
#     "l1_sector": {
#         "description": "Level-1 sector. Fixed per company, so rarely useful as a filter.",
#         "examples": ["Financial Services"],
#     },
#     "l2_industry_group": {
#         "description": "Level-2 industry group. Fixed per company, so rarely useful as a filter.",
#         "examples": ["Insurance"],
#     },
#     "l3_sub_sector": {
#         "description": "Level-3 sub-sector. Fixed per company, so rarely useful as a filter.",
#         "examples": ["Insurance Distribution"],
#     },
#     "l4_segment": {
#         "description": "Level-4 segment. Fixed per company, so rarely useful as a filter.",
#         "examples": [],
#     },
#     "document_subtype": {
#         "description": "Kind of document, e.g. diligence record, board deck, MIS, financials, term sheet, SHA. "
#                        "Use when the user asks for a specific kind of document (due diligence, board pack, etc.).",
#         "examples": ["Diligence Record"],
#     },
#     "author_group": {
#         "description": "Category of author/advisor that prepared the document (e.g. PACES).",
#         "examples": ["PACES"],
#     },
#     "author_org_name": {
#         "description": "Organisation that authored the document (e.g. Alea Consulting). "
#                        "Use when the user names the advisor, auditor or consultant.",
#         "examples": ["Alea Consulting"],
#     },
#     "doc_status": {
#         "description": "Document status such as Draft or Final. Use only if the user asks for draft/final versions.",
#         "examples": ["Final"],
#     },
#     "tier": {
#         "description": "Internal document tier (T1, T2, T3 ...). Use only if the user mentions tier explicitly.",
#         "examples": ["T3"],
#     },
#     "date_prepared": {
#         "description": "Date the document was prepared (exact string match). Prefer reporting_period for time questions.",
#         "examples": [],
#     },
#     "round": {
#         "description": "Investment/funding round the document relates to (e.g. Series A, Series B).",
#         "examples": [],
#     },
#     "tranche": {
#         "description": "Investment tranche the document relates to.",
#         "examples": [],
#     },
#     "reporting_period": {
#         "description": "Period the document reports on (e.g. FY23, Q2 FY24). Use for time-bound questions.",
#         "examples": [],
#     },
#     "fund": {
#         "description": "TVS Capital fund the investment belongs to (e.g. Fund-3).",
#         "examples": ["Fund-3"],
#     },
# }


# FILTERABLE_FIELDS = list(METADATA_SCHEMA.keys())
# CITATION_FIELDS = ["file_name", "current_path", "entity_name"]
# ALL_METADATA_FIELDS = CITATION_FIELDS + FILTERABLE_FIELDS


"""
TVS Capital document metadata schema (from the client's metadata taxonomy sheet).

Each field has:
  description     -> what the field means (shown to the filter LLM)
  controlled      -> "Yes" (fixed vocabulary) | "Part" (partly free text) | "No" (free text)
  applies_to      -> which business areas populate the field
  allowed_values  -> the controlled vocabulary (fallback when live facet values can't be read)
  format          -> value pattern for pattern-based fields (reporting_period, round, tranche)

The filter node prefers live facet values from the index; allowed_values is the fallback.
"""

NOT_AVAILABLE = "Not Available"
ALL_AREAS = "All 10 business areas"

# ───────────────────────── Sector taxonomy: L1 -> L2 -> L3 -> [L4] ─────────────────────────
SECTOR_TAXONOMY: dict[str, dict[str, dict[str, list[str]]]] = {
    "Financial Services": {
        "Lending": {k: [] for k in [
            "Housing Finance", "Vehicle Finance", "Gold Loans", "Unsecured Personal Loans", "Education Finance",
            "MSME Lending", "Supply Chain Finance", "Microfinance", "Agri & Rural Finance",
            "Corporate & Structured Credit", "Banking", "Other-Lending"]},
        "Insurance": {k: [] for k in [
            "Life Insurance", "General Insurance", "Health Insurance", "Reinsurance",
            "Insurance Distribution", "Other-Insurance"]},
        "Payments": {k: [] for k in [
            "Consumer Payments", "Merchant Payments", "Cross-Border Payments", "Other-Payments"]},
        "Wealth & Capital Markets": {k: [] for k in [
            "PE/VC Funds", "Wealth Management", "Broking & Trading", "Fixed Income"]},
        "Tech for Finance": {k: [] for k in [
            "Tech for Lending", "Tech for Insurance", "Tech for Payments", "Tech for Wealth",
            "Banking Infrastructure", "Regtech & Compliance", "CFO Stack", "Financial Data & Analytics"]},
    },
    "Healthcare": {
        "Healthcare Delivery": {k: [] for k in [
            "Hospitals", "Single-Specialty Chains", "Diagnostics & Labs", "Primary Care", "Home & Elder Care"]},
        "Pharma & Life Sciences": {k: [] for k in [
            "Formulations", "APIs & Intermediates", "CDMO & CRAMS", "CRO & Clinical Research", "Biotech & Vaccines"]},
        "Medical Products": {k: [] for k in [
            "Devices & Equipment", "Consumables & Disposables", "Implants"]},
        "Health Technology": {k: [] for k in [
            "Care Delivery Platforms", "E-Pharmacy", "Provider & Payer Software"]},
        "Wellness & Fitness": {k: [] for k in [
            "Nutrition & Supplements", "Fitness & Preventive"]},
    },
    "Technology": {
        "Software": {
            "Vertical SaaS": ["HealthTech", "LegalTech", "RetailTech", "AgriTech", "EdTech", "LogisticsTech", "PropTech"],
            "Horizontal SaaS": ["HRTech", "DevTools", "Data and Analytics", "Security", "MarTech", "FinOps", "Cybersecurity"],
        },
        "Artificial Intelligence": {k: [] for k in [
            "AI Infrastructure", "AI Applications", "Foundation Models"]},
        "IT Services": {k: [] for k in [
            "Application Services", "Cloud & Infrastructure Services", "Data Services", "Engineering R&D Services"]},
        "Consumer Internet": {k: [] for k in [
            "Marketplaces & Platforms", "Gaming", "Social & Content"]},
    },
    "Consumer": {
        "Food & Beverage": {k: [] for k in ["Packaged Foods", "Beverages", "Food Services & QSR"]},
        "Apparel & Lifestyle": {k: [] for k in [
            "Apparel & Footwear", "Beauty & Personal Care", "Accessories", "Home & Living"]},
        "Retail & Commerce": {k: [] for k in [
            "Speciality Retail", "Grocery & General Retail", "E-commerce", "Consumer Durables"]},
        "Consumer Services": {k: [] for k in [
            "Education", "Travel & Hospitality", "Media & Entertainment", "Personal & Household Services"]},
    },
    "Manufacturing & Industrials": {
        "Aerospace & Defense": {k: [] for k in [
            "Components & Materials", "Sub-Systems", "Systems Integration", "Platform Manufacturing"]},
        "Industrial Services": {k: [] for k in [
            "Shipping & Marine Services", "Trading & Distribution", "Technology Distribution", "Logistics & Freight",
            "Port & Terminal Operations", "EPC & Project Services", "Engineering & Design Services",
            "Environmental Services", "Diversified Services"]},
        "Electrical & Energy Equipment": {k: [] for k in [
            "Conductors & Cables", "Power Components", "Power Electronics", "Raw Materials & Components",
            "Energy Storage", "Power Systems", "Renewable Energy Systems", "End Products"]},
        "Electronics & Technology Hardware": {k: [] for k in [
            "Subsystems & Modules", "EMS / Contract Assembly", "OEM / System Integration"]},
        "Auto & Mobility": {k: [] for k in [
            "Raw Material Processing", "Component Manufacturing", "System & Module Supply", "Vehicle OEM",
            "Tires & Rubber"]},
        "Capital Goods & Machinery": {k: [] for k in [
            "Precision Components", "Tools & Consumables", "Fluid & Flow Equipment", "Process Equipment",
            "Process Machinery", "Material Handling", "Heavy Equipment", "Farm Equipment",
            "General Industrial Machinery", "Diversified Manufacturing"]},
        "Chemicals": {k: [] for k in [
            "Basic Chemicals", "Intermediates", "Polymers & Plastics", "Specialty & Performance Chemicals",
            "End-Use Formulations", "Agrochemicals"]},
        "Metals & Mining": {k: [] for k in [
            "Mining & Raw Materials", "Primary Metal Production", "Secondary / Processed Metal",
            "Specialty Metals & Alloys", "Downstream Products"]},
        "Building Materials & Products": {k: [] for k in [
            "Raw Materials", "Bulk Materials", "Processed Materials", "Finished Products"]},
        "Packaging & Paper": {k: [] for k in ["Pulp & Paper", "Flexible Packaging", "Rigid Packaging"]},
        "Textiles & Apparel": {k: [] for k in [
            "Textile Machinery", "Fiber", "Yarn", "Fabric", "Technical Textiles", "Finished Products",
            "Integrated Manufacturing"]},
    },
    "Agriculture & Food": {
        "Agri Inputs": {k: [] for k in [
            "Seeds", "Crop Protection & Nutrition", "Farm Equipment", "Other-Agri-Inputs"]},
        "Agri Supply Chain": {k: [] for k in [
            "Post-Harvest & Processing", "Cold Chain & Storage", "Agri Marketplaces", "Other-Agri-Supply-Chain"]},
        "AgriTech": {k: [] for k in [
            "Farm Management & Advisory", "Animal Protein & Aqua", "Other-AgriTech"]},
    },
    "Energy & Utilities": {
        "Renewables": {k: [] for k in ["Solar", "Wind & Hydro", "Storage & Grid", "Green Fuels", "Other-Renewables"]},
        "Conventional Energy": {k: [] for k in ["Oil & Gas", "Coal & Thermal", "Other-Conventional"]},
        "Utilities & Environment": {k: [] for k in [
            "Power Utilities", "Water & Waste", "Energy Services", "Other-Utilities"]},
    },
    "Real Estate & Construction": {
        "Real Estate": {k: [] for k in ["Residential", "Commercial", "Real Estate Alternatives"]},
        "Construction & Infrastructure": {k: [] for k in ["Construction Services", "Infrastructure Assets"]},
    },
    "Business Services": {
        "Professional Services": {k: [] for k in ["Consulting & Advisory", "Accounting & Tax", "Legal Services"]},
        "Outsourcing & Operations": {k: [] for k in ["BPO", "KPO", "Facility & Workforce Services"]},
        "Marketing & Distribution Services": {k: [] for k in ["Marketing Services", "Distribution & Trading"]},
    },
    "Media & Telecom": {
        "Telecom": {k: [] for k in ["Telecom Services", "Telecom Infrastructure"]},
        "Media": {k: [] for k in ["Broadcast & Print", "Digital Media"]},
    },
    "Macro": {  # L2 only — no L3/L4
        k: {} for k in [
            "Growth & Output", "Prices & Monetary", "Fiscal & Policy", "External Sector",
            "Demographics & Employment", "Macro Themes",
            "Cross sector?",  # TODO: confirm exact value with client — sheet shows it with a '?'
        ]
    },
}


def _unique(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


L1_SECTORS = list(SECTOR_TAXONOMY)
L2_INDUSTRY_GROUPS = _unique(l2 for l1 in SECTOR_TAXONOMY.values() for l2 in l1)
L3_SUB_SECTORS = _unique(l3 for l1 in SECTOR_TAXONOMY.values() for l2 in l1.values() for l3 in l2)
L4_SEGMENTS = _unique(l4 for l1 in SECTOR_TAXONOMY.values() for l2 in l1.values() for l3 in l2.values() for l4 in l3)


def sector_path(l3_sub_sector: str) -> tuple[str, str] | None:
    """Return (l1, l2) for an L3 value — first match (some L3 names repeat across groups)."""
    for l1, groups in SECTOR_TAXONOMY.items():
        for l2, subs in groups.items():
            if l3_sub_sector in subs:
                return l1, l2
    return None


# ───────────────────────── Field schema ─────────────────────────
METADATA_SCHEMA = {
    "business_area": {
        "description": "Business area / function of TVS Capital that owns the document.",
        "controlled": "Yes", "applies_to": ALL_AREAS,
        "allowed_values": ["Origination", "Portfolio", "Research", "Finance", "HR", "Digital", "Legal",
                           "Admin", "Client Relations", "CIO Office"],
    },
    "entity_type": {
        "description": "What the document is about: a single Company, a whole Sector, or TCF itself (firm-level).",
        "controlled": "Yes", "applies_to": ALL_AREAS,
        "allowed_values": ["Company", "Sector", "TCF"],
    },
    "l1_sector": {
        "description": "Level-1 sector of the entity. Constant for a company — rarely useful as a filter "
                       "once the company is known.",
        "controlled": "Yes", "applies_to": ALL_AREAS,
        "allowed_values": L1_SECTORS,
    },
    "l2_industry_group": {
        "description": "Level-2 industry group under the L1 sector (e.g. Insurance under Financial Services).",
        "controlled": "Yes", "applies_to": ALL_AREAS,
        "allowed_values": L2_INDUSTRY_GROUPS,
    },
    "l3_sub_sector": {
        "description": "Level-3 sub-sector under the L2 group (e.g. Insurance Distribution under Insurance).",
        "controlled": "Yes", "applies_to": ALL_AREAS,
        "allowed_values": L3_SUB_SECTORS,
    },
    "l4_segment": {
        "description": "Level-4 segment — only used under Technology > Software (Vertical/Horizontal SaaS). "
                       "Usually 'Not Available' for other sectors.",
        "controlled": "Yes", "applies_to": ALL_AREAS,
        "allowed_values": L4_SEGMENTS,
    },
    "document_subtype": {
        "description": "Kind of document. Map the user's wording: 'due diligence/DD' -> Diligence Record; "
                       "'board deck/board pack' -> Board Material; 'IC note/IC memo' -> IC Record; "
                       "'minutes/MoM/meeting' -> Meeting Notes; 'model' -> Financial Model; "
                       "'MIS/financials' -> Financial Data; 'shareholders agreement' -> SHA; "
                       "'share subscription agreement' -> SSA; 'share purchase agreement' -> SPA; "
                       "'cap table' -> Shareholding.",
        "controlled": "Yes", "applies_to": ALL_AREAS,
        "allowed_values": [
            "Diligence Record", "Financial Model", "Financial Data", "Financial Analysis", "Research Data",
            "Research Report", "Knowledge Sharing", "Fund/Firm Strategy", "Processes and Policies",
            "Board Material", "IC Record", "Action Tracker", "Company Pack", "Valuation Note", "Intro Note",
            "Concept Note", "IIC Note", "Meeting Notes", "BPRC Note", "Exit Note", "L0 Note", "L1 Note",
            "L2 Note", "Event Pack", "SHA", "SSA", "SPA", "NDA", "Shareholding", "Process Agreement",
            "Co-Investment Agreement",
        ],
    },
    "author_group": {
        "description": "Category of whoever prepared the document: TCF (internal), the Company itself, "
                       "a Banker/Fund, a Research House, PACES (external advisors/consultants/auditors), "
                       "or a Government / Regulator.",
        "controlled": "Part", "applies_to": ALL_AREAS,
        "allowed_values": ["TCF", "Company", "Banker/Fund", "Research House", "PACES", "Government / Regulator"],
    },
    "author_org_name": {
        "description": "Name of the contributing organisation (e.g. Alea Consulting). Free text — use only when "
                       "the user names the advisor/auditor/consultant and the value exists in the index.",
        "controlled": "No", "applies_to": ALL_AREAS,
        "allowed_values": [],
    },
    "doc_status": {
        "description": "Final = current approved version; Superseded = an older version replaced by a newer one. "
                       "Drafts are not tracked as a status.",
        "controlled": "Yes", "applies_to": ALL_AREAS,
        "allowed_values": ["Final", "Superseded"],
    },
    "tier": {
        "description": "Internal document importance tier (T1 highest ... T4), or Archive. "
                       "Filter only if the user mentions tier/archive explicitly.",
        "controlled": "Yes", "applies_to": ALL_AREAS,
        "allowed_values": ["T1", "T2", "T3", "T4", "Archive"],
    },
    "date_prepared": {
        "description": "Date the document was prepared, taken from the SharePoint field (exact string). "
                       "Only filter when an exact value is listed; otherwise keep the date in search_query.",
        "controlled": "Part", "applies_to": ALL_AREAS,
        "allowed_values": [],
    },
    "round": {
        "description": "Investment round TVS Capital participated in (Portfolio documents only).",
        "controlled": "Yes", "applies_to": "Portfolio only",
        "format": "R<n>  e.g. R1, R2, R3, R4",
        "allowed_values": ["R1", "R2", "R3", "R4"],
    },
    "tranche": {
        "description": "Tranche of the investment within a round (Portfolio documents only).",
        "controlled": "Yes", "applies_to": "Portfolio only",
        "format": "Tranche <n>  e.g. Tranche 1",
        "allowed_values": ["Tranche 1", "Tranche 2", "Tranche 3"],
    },
    "reporting_period": {
        "description": "Period the document reports on (Portfolio documents only). Convert the user's period into "
                       "this format: 'March 2025' -> Mar-2025; 'Q4 FY25' -> Q4 FY25; 'FY 2024-25' -> FY25; "
                       "'first half FY25' -> H1 FY25; 'calendar 2024' -> CY24. 'Point in Time' = a snapshot "
                       "with no period.",
        "controlled": "Yes", "applies_to": "Portfolio only",
        "format": "Mon-YYYY | Q<n> FY<yy> | H<n> FY<yy> | FY<yy> | Q<n> CY<yy> | H<n> CY<yy> | CY<yy> | Point in Time",
        "allowed_values": ["Point in Time"],  # rest are pattern-based; live facet values take priority
    },
    "fund": {
        "description": "TVS Capital fund the deal belongs to (Origination & Portfolio documents); "
                       "Firm-Level = not tied to a single fund.",
        "controlled": "Yes", "applies_to": "Origination, Portfolio",
        "allowed_values": ["Fund-1A", "Fund-1B", "Fund-3", "Fund-4", "Firm-Level"],
    },
}

# Free-text / routing fields (not LLM-filterable)
REFERENCE_FIELDS = {
    "file_name": "File name as on the drive (free text).",
    "current_path": "Full path from the SharePoint library root (free text).",
    "entity_name": "Company name / L1 sector node name / TCF — applied automatically by the router.",
}

# Fields the LLM may filter on. entity_name is applied by routing; file_name/current_path are for citations.
FILTERABLE_FIELDS = list(METADATA_SCHEMA.keys())
CITATION_FIELDS = ["file_name", "current_path", "entity_name"]
ALL_METADATA_FIELDS = CITATION_FIELDS + FILTERABLE_FIELDS

# Backward compatibility: search.py falls back to spec["examples"]; format hint folded into the description
for _spec in METADATA_SCHEMA.values():
    _spec.setdefault("examples", _spec["allowed_values"])
    if _spec.get("format"):
        _spec["description"] = f"{_spec['description']} Format: {_spec['format']}."
