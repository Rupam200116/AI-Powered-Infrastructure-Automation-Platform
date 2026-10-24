# agent/providers.py
# Single source of truth for "what clouds do we support and what services
# does each one offer". Backend, planner, and codegen all import from here
# so we never have provider-specific strings scattered around the codebase.

PROVIDERS = {
    "aws": {
        "label": "Amazon Web Services",
        "color": "#FF9900",
        "default_region": "ap-south-1",       # Mumbai
        "region_label": "Region",
        "services": {
            "EC2":        {"label": "EC2",             "desc": "Virtual Server",   "icon": "🖥️", "color": "#FF9900"},
            "S3":         {"label": "S3",               "desc": "Object Storage",   "icon": "🪣", "color": "#7AA116"},
            "RDS":        {"label": "RDS",              "desc": "Managed Database", "icon": "🗄️", "color": "#527FFF"},
            "VPC":        {"label": "VPC",              "desc": "Virtual Network",  "icon": "🌐", "color": "#8C4FFF"},
            "Lambda":     {"label": "Lambda",           "desc": "Serverless",       "icon": "λ",  "color": "#ED7100"},
            "CloudWatch": {"label": "CloudWatch",       "desc": "Monitoring",       "icon": "📊", "color": "#E7157B"},
            "IAM":        {"label": "IAM",              "desc": "Access Control",   "icon": "🔐", "color": "#DD344C"},
            "EKS":        {"label": "EKS",              "desc": "Kubernetes",       "icon": "☸️", "color": "#326CE5"},
        },
        # instance size dropdown only makes sense for the "VM" service
        "vm_service": "EC2",
        "vm_sizes": [
            {"value": "t2.micro",  "label": "t2.micro  — Free Tier"},
            {"value": "t3.small",  "label": "t3.small  — ~$15/mo"},
            {"value": "t3.medium", "label": "t3.medium — ~$30/mo"},
            {"value": "t3.large",  "label": "t3.large  — ~$60/mo"},
            {"value": "m5.xlarge", "label": "m5.xlarge — ~$140/mo"},
        ],
        "default_vm_size": "t2.micro",
    },
    "azure": {
        "label": "Microsoft Azure",
        "color": "#0078D4",
        "default_region": "centralindia",
        "region_label": "Location",
        "services": {
            "VM":       {"label": "Virtual Machine", "desc": "Virtual Server",   "icon": "🖥️", "color": "#0078D4"},
            "Blob":     {"label": "Blob Storage",     "desc": "Object Storage",   "icon": "🪣", "color": "#33C9C9"},
            "SQLDB":    {"label": "Azure SQL DB",     "desc": "Managed Database", "icon": "🗄️", "color": "#00188F"},
            "VNet":     {"label": "VNet",             "desc": "Virtual Network",  "icon": "🌐", "color": "#50E6FF"},
            "Function": {"label": "Functions",        "desc": "Serverless",       "icon": "λ",  "color": "#FFB900"},
            "Monitor":  {"label": "Monitor",          "desc": "Monitoring",       "icon": "📊", "color": "#68217A"},
            "RBAC":     {"label": "RBAC / Entra ID",  "desc": "Access Control",   "icon": "🔐", "color": "#E81123"},
            "AKS":      {"label": "AKS",              "desc": "Kubernetes",       "icon": "☸️", "color": "#326CE5"},
        },
        "vm_service": "VM",
        "vm_sizes": [
            {"value": "Standard_B1s",  "label": "Standard_B1s  — Free Tier eligible"},
            {"value": "Standard_B2s",  "label": "Standard_B2s  — ~$30/mo"},
            {"value": "Standard_D2s_v3", "label": "Standard_D2s_v3 — ~$70/mo"},
            {"value": "Standard_D4s_v3", "label": "Standard_D4s_v3 — ~$140/mo"},
        ],
        "default_vm_size": "Standard_B1s",
    },
    "gcp": {
        "label": "Google Cloud Platform",
        "color": "#4285F4",
        "default_region": "asia-south1",       # Mumbai
        "region_label": "Region",
        "services": {
            "ComputeEngine": {"label": "Compute Engine", "desc": "Virtual Server",   "icon": "🖥️", "color": "#4285F4"},
            "CloudStorage":  {"label": "Cloud Storage",  "desc": "Object Storage",   "icon": "🪣", "color": "#34A853"},
            "CloudSQL":      {"label": "Cloud SQL",      "desc": "Managed Database", "icon": "🗄️", "color": "#EA4335"},
            "VPC":           {"label": "VPC",            "desc": "Virtual Network",  "icon": "🌐", "color": "#FBBC05"},
            "CloudFunctions":{"label": "Cloud Functions","desc": "Serverless",       "icon": "λ",  "color": "#F4B400"},
            "CloudMonitoring":{"label": "Cloud Monitoring","desc": "Monitoring",     "icon": "📊", "color": "#AB47BC"},
            "IAM":           {"label": "IAM",            "desc": "Access Control",   "icon": "🔐", "color": "#00ACC1"},
            "GKE":           {"label": "GKE",            "desc": "Kubernetes",       "icon": "☸️", "color": "#326CE5"},
        },
        "vm_service": "ComputeEngine",
        "vm_sizes": [
            {"value": "e2-micro",  "label": "e2-micro  — Free Tier eligible"},
            {"value": "e2-small",  "label": "e2-small  — ~$15/mo"},
            {"value": "e2-medium", "label": "e2-medium — ~$30/mo"},
            {"value": "n2-standard-2", "label": "n2-standard-2 — ~$70/mo"},
        ],
        "default_vm_size": "e2-micro",
    },
}


def validate_provider(provider: str) -> str:
    provider = (provider or "").strip().lower()
    if provider not in PROVIDERS:
        raise ValueError(f"Unsupported cloud provider: {provider!r}. Choose one of {list(PROVIDERS)}")
    return provider


def validate_services(provider: str, services: list) -> list:
    valid = set(PROVIDERS[provider]["services"].keys())
    unknown = [s for s in services if s not in valid]
    if unknown:
        raise ValueError(f"Unknown services for {provider}: {unknown}. Valid: {sorted(valid)}")
    return services


def catalog_for_frontend() -> dict:
    """Shape the catalog for the /api/providers endpoint the frontend calls."""
    return {
        key: {
            "label": cfg["label"],
            "color": cfg["color"],
            "region_label": cfg["region_label"],
            "default_region": cfg["default_region"],
            "services": [
                {"id": sid, **meta} for sid, meta in cfg["services"].items()
            ],
            "vm_service": cfg["vm_service"],
            "vm_sizes": cfg["vm_sizes"],
            "default_vm_size": cfg["default_vm_size"],
        }
        for key, cfg in PROVIDERS.items()
    }
