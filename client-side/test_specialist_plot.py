import city
import city_plots

pCity = city.cityByName("Rome")
cp = city_plots.CityPlots(pCity)

# Define plot priorities and preferred specialist fallback hierarchy:
plot_priority = ("PRODUCTION", "COMMERCE", "FOOD")
specialist_hierarchy = [
    "SPECIALIST_SCIENTIST",   # Fill Scientists first (if Library/University slots exist)
    "SPECIALIST_ENGINEER",    # Fill Engineers second (Forge/Factory)
    "SPECIALIST_MERCHANT",    # Fill Merchants third (Market/Bank)
    "SPECIALIST_CITIZEN"      # Standard fallback
]

# Run the combined manager with a zero starvation guarantee:
cp.assignPlotsAndFillSpecialists(
    yield_priority=plot_priority,
    specialist_priority=specialist_hierarchy,
    iMinFoodBuffer=0
)
