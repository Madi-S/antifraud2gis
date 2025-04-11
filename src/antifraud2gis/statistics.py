import dataclasses

@dataclasses.dataclass
class Statistics:
    total_users_loaded: int
    total_companies_loaded: int
    total_users_loaded_network: int
    total_companies_loaded_network: int
    created_new_companies: int = 0

statistics = Statistics(
    total_users_loaded=0,
    total_companies_loaded=0,
    total_users_loaded_network=0,
    total_companies_loaded_network=0,
    created_new_companies=0
)
