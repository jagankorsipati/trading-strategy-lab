from dataclasses import dataclass


@dataclass(frozen=True)
class FixedQuantitySizer:
    quantity: int

    def size(self, price: float, available_capital: float) -> int:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if price <= 0:
            raise ValueError("price must be positive")
        return self.quantity
