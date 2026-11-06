import pandas as pd
import os

print("=== 1. PRODUCT CATALOGUE AUDIT ===")
prod = pd.read_csv("YTL_TrackA_Udyam_Digital_Data/product_catalogue.csv")
print(f"Total Products: {len(prod)}")
print("Categories:", prod["category"].value_counts().to_dict())
print("Requires GST count:", prod["requires_gstin"].value_counts().to_dict())
print("Requires One Of rules:", prod[prod["requires_one_of"].notna()][["product_id", "product_name", "requires_one_of"]].to_dict("records"))

print("\n=== 2. MOCK REGISTRIES AUDIT ===")
gst = pd.read_csv("YTL_TrackA_Udyam_Digital_Data/mock_gstin_registry.csv")
print(f"Total GSTIN records: {len(gst)}")
print("GST Status counts:", gst["status"].value_counts().to_dict())

udyam = pd.read_csv("YTL_TrackA_Udyam_Digital_Data/mock_udyam_registry.csv")
print(f"Total Udyam records: {len(udyam)}")

print("\n=== 3. KYC APPLICANTS AUDIT (K01 - K12) ===")
docs = sorted(os.listdir("YTL_TrackA_Udyam_Digital_Data/kyc_documents"))
applicants = sorted(list(set(d.split("_")[0] for d in docs)))
print(f"Found {len(applicants)} applicants: {applicants}")
for a in applicants:
    adocs = [d for d in docs if d.startswith(a)]
    print(f"  {a}: {len(adocs)} files -> {', '.join(adocs)}")

print("\n=== 4. LEADS DATA AUDIT ===")
leads = pd.read_csv("YTL_TrackA_Udyam_Digital_Data/smb_leads.csv")
print(f"Total Leads: {len(leads)}")
print("Funnel Stage Counts:\n", leads["stage_reached"].value_counts().to_dict())
print("Language Distribution:\n", leads["preferred_language"].value_counts().to_dict())
print("Top 5 Drop Reasons:\n", leads["drop_reason"].value_counts().head(5).to_dict())

