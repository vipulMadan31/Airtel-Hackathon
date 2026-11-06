import pandas as pd
from app.config import (
    PRODUCT_CATALOGUE_PATH,
    MOCK_GSTIN_REGISTRY_PATH,
    MOCK_UDYAM_REGISTRY_PATH,
    SMB_LEADS_PATH
)

class DataLoader:
    _instance = None

    def __init__(self):
        self.products_df = pd.read_csv(PRODUCT_CATALOGUE_PATH)
        # Clean string nulls
        self.products_df["requires_one_of"] = self.products_df["requires_one_of"].fillna("")
        self.products_df["target_segments"] = self.products_df["target_segments"].fillna("")
        self.products_df["available_city_tiers"] = self.products_df["available_city_tiers"].astype(str)

        self.gstin_df = pd.read_csv(MOCK_GSTIN_REGISTRY_PATH)
        self.gstin_index = {row["gstin"].strip().upper(): row.to_dict() for _, row in self.gstin_df.iterrows()}

        self.udyam_df = pd.read_csv(MOCK_UDYAM_REGISTRY_PATH)
        self.udyam_index = {row["udyam_number"].strip().upper(): row.to_dict() for _, row in self.udyam_df.iterrows()}

        self.leads_df = pd.read_csv(SMB_LEADS_PATH)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DataLoader()
        return cls._instance

    def get_all_products(self):
        return self.products_df.to_dict(orient="records")

    def get_product(self, product_id: str):
        match = self.products_df[self.products_df["product_id"] == product_id]
        if not match.empty:
            return match.iloc[0].to_dict()
        return None

    def lookup_gstin(self, gstin: str):
        return self.gstin_index.get(gstin.strip().upper())

    def lookup_udyam(self, udyam_number: str):
        return self.udyam_index.get(udyam_number.strip().upper())

    def get_stalled_leads(self, limit: int = 20):
        dropped = self.leads_df[self.leads_df["outcome"] == "Dropped"]
        return dropped.head(limit).to_dict(orient="records")

