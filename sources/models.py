from dataclasses import dataclass
from typing import Optional

@dataclass
class Deal:
    model: str  # "Huawei Watch D2" or "Huawei Watch D3"
    title: str
    store: str  # "eBay", "AliExpress", "WondaMobile", "Amazon", "Giztop", etc.
    item_price_cad: float
    shipping_price_cad: float
    total_price_cad: float
    url: str
    is_global_version: bool
    condition: str  # "Brand New", "Refurbished", etc.
    details: Optional[str] = ""

    def summary(self) -> str:
        return (
            f"[{self.model}] {self.title}\n"
            f"  • Store: {self.store}\n"
            f"  • Item: ${self.item_price_cad:.2f} CAD | Shipping to CA: ${self.shipping_price_cad:.2f} CAD\n"
            f"  • Total Landed Cost: ${self.total_price_cad:.2f} CAD\n"
            f"  • Condition: {self.condition} | Global: {'Yes' if self.is_global_version else 'Check Listing'}\n"
            f"  • Link: {self.url}"
        )
