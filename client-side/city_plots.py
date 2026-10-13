import city
from CvPythonExtensions import *

gc = city.gc()

class YieldPlots(object):

    def __init__(self,cyPlot):
        # Retrieve net calculated yield for each yield type
        self.cyPlot = cyPlot
        self.iFoodYield       = cyPlot.calculateYield(YieldTypes.YIELD_FOOD, True)
        self.iProductionYield = cyPlot.calculateYield(YieldTypes.YIELD_PRODUCTION, True)
        self.iCommerceYield   = cyPlot.calculateYield(YieldTypes.YIELD_COMMERCE, True)

    def getYieldValue(self, eYieldType):
        """Helper to get a single yield value by YieldTypes enum or String tag."""
        if eYieldType in (YieldTypes.YIELD_FOOD, "FOOD", "Food", 0):
            return self.iFoodYield
        elif eYieldType in (YieldTypes.YIELD_PRODUCTION, "PRODUCTION", "Production", "HAMMERS", 1):
            return self.iProductionYield
        elif eYieldType in (YieldTypes.YIELD_COMMERCE, "COMMERCE", "Commerce", 2):
            return self.iCommerceYield
        return 0

class CityPlots(object):


    def __init__(self, cy):
        self.cy = cy
        self.all_plots = []
        self.workable_plots = []
        self.worked_plots = []
        self.getCityPlots()


    def getCityPlots(self):
        gc = city.gc()
        for i in range(gc.getNUM_CITY_PLOTS()):
            pPlot = self.cy.getCityIndexPlot(i)
            if pPlot and not pPlot.isNone():
                self.all_plots.append(pPlot)
                
                # Check if city can work this plot
                if self.cy.canWork(pPlot):
                    self.workable_plots.append(pPlot)
                    
                # Check if a citizen is currently working this plot
                if self.cy.isWorkingPlot(pPlot):
                    self.worked_plots.append(pPlot)

    def printPlotYields(self):
        for plot in self.workable_plots:
            # Safe check to prevent Civ IV crashes if a plot pointer is invalid
            if plot and not plot.isNone():
                yield_plot = YieldPlots(plot)
                # %d string formatting is cleaner and faster in Python 2.4 than + str()
                print " food: %d production: %d commerce: %d" % (
                    yield_plot.iFoodYield, 
                    yield_plot.iProductionYield, 
                    yield_plot.iCommerceYield
                )

    def getOrderedYieldPlots(self, eYieldType, bDescending=True):
        """
        Returns an ordered list of YieldPlots objects for workable plots,
        sorted by the specified YieldType (e.g. YieldTypes.YIELD_FOOD or "FOOD").
        """
        yield_plots = []
        for pPlot in self.workable_plots:
            if pPlot and not pPlot.isNone():
                yield_plots.append(YieldPlots(pPlot))

        # Helper key function for Python 2.4 sorting
        def extract_yield(yp):
            if eYieldType in (YieldTypes.YIELD_FOOD, "FOOD", "Food", 0):
                return yp.iFoodYield
            elif eYieldType in (YieldTypes.YIELD_PRODUCTION, "PRODUCTION", "Production", 1):
                return yp.iProductionYield
            elif eYieldType in (YieldTypes.YIELD_COMMERCE, "COMMERCE", "Commerce", 2):
                return yp.iCommerceYield
            return 0

        # Sort in-place using key function
        yield_plots.sort(key=extract_yield, reverse=bDescending)
        return yield_plots

    def assignWorkablePlotsByYield(self, eYieldType, bDescending=True):
        """
        Clears existing plot assignments and re-assigns workers to the highest-yielding
        workable plots based on eYieldType (e.g. YieldTypes.YIELD_FOOD, YIELD_PRODUCTION, YIELD_COMMERCE).
        """
        pCity = self.cy
        if not pCity or pCity.isNone():
            return

        # 1. Store the total number of working citizens before clearing
        iWorkersToAssign = pCity.getWorkingPopulation()

        # 2. Clear all currently worked plots (index 1 to 20; skip index 0 city center)
        for iIndex in range(1, 21):
            pPlot = pCity.getCityIndexPlot(iIndex)
            if pPlot and not pPlot.isNone():
                if pCity.isWorkingPlot(pPlot):
                    pCity.alterWorkingPlot(iIndex)  # Toggles worked status to False

        # 3. Fetch the ordered list of YieldPlots
        sorted_yield_plots = self.getOrderedYieldPlots(eYieldType, bDescending)

        # 4. Assign workers to the top plots up to iWorkersToAssign
        iAssigned = 0
        for yp in sorted_yield_plots:
            pPlot = yp.cyPlot
            if not pPlot or pPlot.isNone():
                continue

            iIndex = pCity.getCityPlotIndex(pPlot)

            # Skip city center plot (index 0 is worked automatically)
            if iIndex <= 0:
                continue

            if iAssigned < iWorkersToAssign:
                if pCity.canWork(pPlot) and not pCity.isWorkingPlot(pPlot):
                    pCity.alterWorkingPlot(iIndex)  # Toggles worked status to True
                    iAssigned += 1

        # 5. Refresh internal worked_plots list
        self.worked_plots = []
        for i in range(21):
            pPlot = pCity.getCityIndexPlot(i)
            if pPlot and not pPlot.isNone() and pCity.isWorkingPlot(pPlot):
                self.worked_plots.append(pPlot)

        print "Reassigned %d workers in %s based on %s yield." % (
            iAssigned, pCity.getName(), str(eYieldType)
        )

    def getOrderedYieldPlotsByPriority(self, yield_priority):
        """
        Returns workable YieldPlots sorted by a sequence of yield priorities.
        Example yield_priority: ("PRODUCTION", "COMMERCE", "FOOD")
        """
        yield_plots = []
        for pPlot in self.workable_plots:
            if pPlot and not pPlot.isNone():
                yield_plots.append(YieldPlots(pPlot))

        # Build a key function that returns a tuple of yields in the priority order requested
        def priority_key(yp):
            return tuple([yp.getYieldValue(y) for y in yield_priority])

        # Sorts lexicographically: Primary Yield -> Secondary Yield -> Tertiary Yield
        yield_plots.sort(key=priority_key, reverse=True)
        return yield_plots


    def assignWorkablePlotsByPriority(self, *yield_priority):
        """
        Reassigns city workers to maximize plots based on a prioritized yield order.
        Accepts flexible parameters, e.g.:
           assignWorkablePlotsByPriority("PRODUCTION", "COMMERCE", "FOOD")
        or assignWorkablePlotsByPriority(YieldTypes.YIELD_FOOD, YieldTypes.YIELD_PRODUCTION)
        """
        pCity = self.cy
        if not pCity or pCity.isNone():
            return

        # 1. Record number of available working citizens
        iWorkersToAssign = pCity.getWorkingPopulation()

        # 2. Clear current worked tiles (index 1 to 20; skip 0 city center tile)
        for iIndex in range(1, 21):
            pPlot = pCity.getCityIndexPlot(iIndex)
            if pPlot and not pPlot.isNone() and pCity.isWorkingPlot(pPlot):
                pCity.alterWorkingPlot(iIndex)  # Toggle OFF

        # 3. Retrieve plots ordered by priority tuple
        sorted_yield_plots = self.getOrderedYieldPlotsByPriority(yield_priority)

        # 4. Assign top N plots matching available citizen count
        iAssigned = 0
        for yp in sorted_yield_plots:
            pPlot = yp.cyPlot
            if not pPlot or pPlot.isNone():
                continue

            iIndex = pCity.getCityPlotIndex(pPlot)
            if iIndex <= 0:  # Skip city center plot
                continue

            if iAssigned < iWorkersToAssign:
                if pCity.canWork(pPlot) and not pCity.isWorkingPlot(pPlot):
                    pCity.alterWorkingPlot(iIndex)  # Toggle ON
                    iAssigned += 1

        # 5. Refresh worked_plots list
        self.worked_plots = []
        for i in range(21):
            pPlot = pCity.getCityIndexPlot(i)
            if pPlot and not pPlot.isNone() and pCity.isWorkingPlot(pPlot):
                self.worked_plots.append(pPlot)

        print "Reassigned %d workers in %s with priority %s" % (
            iAssigned, pCity.getName(), str(yield_priority)
        )

    def assignWorkablePlotsWithFoodSafety(self, yield_priority, iMinFoodBuffer=0):
        """
        Reassigns city workers based on yield priority while guaranteeing a minimum
        food buffer to prevent starvation.
        
        :param yield_priority: Priority order, e.g. ("PRODUCTION", "COMMERCE", "FOOD")
        :param iMinFoodBuffer: Minimum net food surplus (0 = no starvation, 2 = +1 citizen growth rate)
        """
        pCity = self.cy
        if not pCity or pCity.isNone():
            return

        iWorkersToAssign = pCity.getWorkingPopulation()
        if iWorkersToAssign <= 0:
            return

        # 1. Calculate required food target
        iTotalFoodNeeded = pCity.foodConsumption(False, 0) + iMinFoodBuffer
        
        # Base food from city center plot (index 0 is worked automatically)
        pCityCenter = pCity.getCityIndexPlot(0)
        iCityCenterFood = 0
        if pCityCenter and not pCityCenter.isNone():
            iCityCenterFood = pCityCenter.calculateYield(YieldTypes.YIELD_FOOD, True)

        iFoodRequiredFromWorkers = max(0, iTotalFoodNeeded - iCityCenterFood)

        # 2. Clear currently worked tiles (index 1 to 20)
        for iIndex in range(1, 21):
            pPlot = pCity.getCityIndexPlot(iIndex)
            if pPlot and not pPlot.isNone() and pCity.isWorkingPlot(pPlot):
                pCity.alterWorkingPlot(iIndex)

        # 3. Build candidate YieldPlots list
        candidate_plots = [YieldPlots(p) for p in self.workable_plots if p and not p.isNone()]

        # Sort candidate plots by user priority
        priority_sorted = self.getOrderedYieldPlotsByPriority(yield_priority)

        # Sort candidate plots by Food yield (descending) as a backup safety pool
        food_sorted = sorted(candidate_plots, key=lambda yp: yp.iFoodYield, reverse=True)

        # 4. Select Plots with Food Safety Check
        # First pass: Check if user's priority order naturally satisfies the food target
        selected_plots = priority_sorted[:iWorkersToAssign]
        current_food = sum([yp.iFoodYield for yp in selected_plots])

        # Second pass: If priority selection causes a deficit, force high-food tiles first
        if current_food < iFoodRequiredFromWorkers:
            selected_plots = []
            accumulated_food = 0

            # Step A: Lock in high-food tiles until food target is satisfied
            for yp in food_sorted:
                if len(selected_plots) < iWorkersToAssign and accumulated_food < iFoodRequiredFromWorkers:
                    selected_plots.append(yp)
                    accumulated_food += yp.iFoodYield

            # Step B: Fill remaining worker slots with top priority tiles
            for yp in priority_sorted:
                if yp not in selected_plots and len(selected_plots) < iWorkersToAssign:
                    selected_plots.append(yp)

        # 5. Apply assignments to the city
        iAssigned = 0
        for yp in selected_plots:
            iIndex = pCity.getCityPlotIndex(yp.cyPlot)
            if iIndex > 0 and pCity.canWork(yp.cyPlot):
                pCity.alterWorkingPlot(iIndex)
                iAssigned += 1

        # Calculate final net food surplus/deficit
        final_food = iCityCenterFood + sum([yp.iFoodYield for yp in selected_plots])
        iNetFood = final_food - pCity.foodConsumption(False, 0)

        print "%s Workers Reassigned: %d | Net Food: %+d | Priority: %s" % (
            pCity.getName(), iAssigned, iNetFood, str(yield_priority)
        )

    def assignPlotsAndFillSpecialists(self, yield_priority, specialist_priority=None, iMinFoodBuffer=0):
        """
        Reassigns tile workers based on yield priority (with food safety), 
        then automatically fills remaining unassigned citizens into specialist slots.
        
        :param yield_priority: Priority order for plots, e.g. ("PRODUCTION", "COMMERCE", "FOOD")
        :param specialist_priority: Priority list for specialists, e.g. 
                                   ["SPECIALIST_SCIENTIST", "SPECIALIST_ENGINEER", "SPECIALIST_MERCHANT"]
        :param iMinFoodBuffer: Net food safety threshold (0 = prevent starvation, 2 = growth buffer)
        """
        pCity = self.cy
        if not pCity or pCity.isNone():
            return

        # -------------------------------------------------------------------
        # STEP 1: Clear existing forced specialists first
        # -------------------------------------------------------------------
        for iSpec in range(gc.getNumSpecialistInfos()):
            pCity.setForceSpecialistCount(iSpec, 0)

        # -------------------------------------------------------------------
        # STEP 2: Assign Tile Workers with Food Safety
        # -------------------------------------------------------------------
        # Calculate food requirements
        iTotalFoodNeeded = pCity.foodConsumption(False, 0) + iMinFoodBuffer
        
        pCityCenter = pCity.getCityIndexPlot(0)
        iCityCenterFood = 0
        if pCityCenter and not pCityCenter.isNone():
            iCityCenterFood = pCityCenter.calculateYield(YieldTypes.YIELD_FOOD, True)

        iFoodRequiredFromWorkers = max(0, iTotalFoodNeeded - iCityCenterFood)

        # Clear worked plots (indices 1 to 20)
        for iIndex in range(1, 21):
            pPlot = pCity.getCityIndexPlot(iIndex)
            if pPlot and not pPlot.isNone() and pCity.isWorkingPlot(pPlot):
                pCity.alterWorkingPlot(iIndex)

        # Retrieve and sort candidate yield plots
        candidate_plots = [YieldPlots(p) for p in self.workable_plots if p and not p.isNone()]
        priority_sorted = self.getOrderedYieldPlotsByPriority(yield_priority)
        food_sorted = sorted(candidate_plots, key=lambda yp: yp.iFoodYield, reverse=True)

        iWorkersToAssign = pCity.getWorkingPopulation()
        selected_plots = priority_sorted[:iWorkersToAssign]
        current_food = sum([yp.iFoodYield for yp in selected_plots])

        # Enforce food safety if default priority selection creates a deficit
        if current_food < iFoodRequiredFromWorkers:
            selected_plots = []
            accumulated_food = 0

            # Lock in high-food tiles first
            for yp in food_sorted:
                if len(selected_plots) < iWorkersToAssign and accumulated_food < iFoodRequiredFromWorkers:
                    selected_plots.append(yp)
                    accumulated_food += yp.iFoodYield

            # Fill remaining worker slots with top priority tiles
            for yp in priority_sorted:
                if yp not in selected_plots and len(selected_plots) < iWorkersToAssign:
                    selected_plots.append(yp)

        # Apply plot worker assignments
        iAssignedWorkers = 0
        for yp in selected_plots:
            iIndex = pCity.getCityPlotIndex(yp.cyPlot)
            if iIndex > 0 and pCity.canWork(yp.cyPlot):
                pCity.alterWorkingPlot(iIndex)
                iAssignedWorkers += 1

        # Refresh worked_plots list
        self.worked_plots = [yp.cyPlot for yp in selected_plots]

        # -------------------------------------------------------------------
        # STEP 3: Auto-Fill Unassigned Citizens into Specialists
        # -------------------------------------------------------------------
        iTotalPop = pCity.getPopulation()
        iAngryPop = pCity.angryPopulation(0)
        
        # Calculate citizens available for specialist roles
        iUnassignedCitizens = max(0, iTotalPop - iAssignedWorkers - iAngryPop)

        assigned_specialists = {}
        if iUnassignedCitizens > 0 and specialist_priority:
            for szSpecTag in specialist_priority:
                if iUnassignedCitizens <= 0:
                    break

                eSpec = gc.getInfoTypeForString(szSpecTag)
                if eSpec != -1 and pCity.isSpecialistValid(eSpec, 1):
                    # Check maximum slots allowed by buildings/wonders
                    iMaxAllowed = pCity.getMaxSpecialistCount(eSpec)
                    iCurrentForced = pCity.getForceSpecialistCount(eSpec)

                    # Determine available slots (-1 or large number implies unlimited, e.g., via Civics)
                    if iMaxAllowed > 0:
                        iAvailableSlots = (iMaxAllowed - iCurrentForced) 
                    else:
                        iAvailableSlots = iUnassignedCitizens

                    if iAvailableSlots > 0:
                        iToAssign = min(iUnassignedCitizens, iAvailableSlots)
                        pCity.setForceSpecialistCount(eSpec, iCurrentForced + iToAssign)
                        
                        iUnassignedCitizens -= iToAssign
                        assigned_specialists[szSpecTag] = assigned_specialists.get(szSpecTag, 0) + iToAssign

        print "%s Reassigned -> Tile Workers: %d | Specialists: %s | Idle/Angry: %d" % (
            pCity.getName(), iAssignedWorkers, str(assigned_specialists), iUnassignedCitizens + iAngryPop
        )


