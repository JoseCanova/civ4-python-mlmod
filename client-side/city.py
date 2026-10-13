from CvPythonExtensions import *

def gc():
    return CyGlobalContext()

def player():
    return gc().getActivePlayer()

# ---------------------------------------------------------------------------
# Individual Helper Functions (Returning Raw Values)
# ---------------------------------------------------------------------------

def population(pCity):
    """Returns the city population level index."""
    if pCity and not pCity.isNone():
        return pCity.getPopulation()
    return 0

def realPopulation(pCity):
    """Returns the calculated demographic real-world population count."""
    if pCity and not pCity.isNone():
        return pCity.getRealPopulation()
    return 0

def workingPopulation(pCity):
    """Returns the number of citizens assigned to work tile plots."""
    if pCity and not pCity.isNone():
        return pCity.getWorkingPopulation()
    return 0

# ---------------------------------------------------------------------------
# Structured Return Methods (Dictionary & Tuple)
# ---------------------------------------------------------------------------

def getPopulationStats(pCity):
    """
    Returns a structured dictionary containing all population statistics
    for a given CyCity instance.
    """
    if not pCity or pCity.isNone():
        return None
        
    return {
        "population": pCity.getPopulation(),
        "real_population": pCity.getRealPopulation(),
        "working_population": pCity.getWorkingPopulation(),
        "specialist_population": pCity.getSpecialistPopulation(),
        "angry_population": pCity.angryPopulation(0)
    }

def getPopulationTuple(pCity):
    """
    Returns population statistics as a tuple:
    (population, real_population, working_population)
    """
    if not pCity or pCity.isNone():
        return (0, 0, 0)
        
    return (
        pCity.getPopulation(),
        pCity.getRealPopulation(),
        pCity.getWorkingPopulation()
    )

# ---------------------------------------------------------------------------
# City Lookup & Plot Utilities
# ---------------------------------------------------------------------------

def activePlayerCities():
    play = player()
    cities = []
    (pCity, iter) = play.firstCity(False)
    while pCity and not pCity.isNone():
        cities.append(pCity)
        (pCity, iter) = play.nextCity(iter, False)
    return cities

def cityByName(cityName):
    play = player()
    (pCity, iter) = play.firstCity(False)
    while pCity and not pCity.isNone():
        if pCity.getName() == cityName:
            return pCity
        (pCity, iter) = play.nextCity(iter, False)
    return None

def printCity(cityName):
    city = cityByName(cityName)
    if city and not city.isNone():
        print "City Name : %s" % city.getName()

def workablePlots(pCity):
    if not pCity or pCity.isNone():
        return
    for iIndex in range(21):
        pPlot = pCity.getCityIndexPlot(iIndex)
        if pPlot and not pPlot.isNone():
            if pCity.canWork(pPlot):
                bWorking = pCity.isWorkingPlot(pPlot)
                print "Plot index %d: workable=True, working=%s" % (iIndex, str(bWorking))

def printCityWorkablePlots(cityName):
    city = cityByName(cityName)
    if city and not city.isNone():
        workablePlots(city)

# ---------------------------------------------------------------------------
# Citizen & Specialist Manager Class
# ---------------------------------------------------------------------------

class CityCitizenManager(object):
    def __init__(self, pCity):
        self.pCity = pCity

    def hasForcedSpecialists(self):
        """Returns True if the city contains manually assigned forced specialists."""
        if self.pCity and not self.pCity.isNone():
            return self.pCity.isSpecialistForced()
        return False

    def countUnassignedCitizens(self):
        """Calculates citizens that are idle (not working tiles, assigned, or angry)."""
        if not self.pCity or self.pCity.isNone():
            return 0
            
        iTotal = self.pCity.getPopulation()
        iWorking = self.pCity.getWorkingPopulation()
        iSpecialists = self.pCity.getSpecialistPopulation()
        iAngry = self.pCity.angryPopulation(0)

        iIdle = iTotal - iWorking - iSpecialists - iAngry
        return max(0, iIdle)

    def printCitizenStatus(self):
        if self.pCity and not self.pCity.isNone():
            print "City: %s" % self.pCity.getName()
            print "  Forced Specialists: %s" % str(self.hasForcedSpecialists())
            print "  Unassigned Citizens: %d" % self.countUnassignedCitizens()

    def clearForcedSpecialists(self):
        """Resets all forced specialist counts to 0."""
        if self.pCity and not self.pCity.isNone():
            for i in range(gc().getNumSpecialistInfos()):
                self.pCity.setForceSpecialistCount(i, 0)

    def applySpecialistList(self, specialist_entries):
        """
        Applies a list of specialist entries to the city.
        Example: manager.applySpecialistList([("SPECIALIST_SCIENTIST", 2), ("SPECIALIST_MERCHANT", 1)])
        """
        if not self.pCity or self.pCity.isNone():
            return

        self.clearForcedSpecialists()

        for szTag, iCount in specialist_entries:
            eSpec = gc().getInfoTypeForString(szTag)
            if eSpec != -1 and self.pCity.isSpecialistValid(eSpec, 1):
                iMax = self.pCity.getMaxSpecialistCount(eSpec)
            # Standard if-else block
            if iMax > 0:
                iToAssign = min(iCount, iMax)
            else:
                iToAssign = iCount  
            self.pCity.setForceSpecialistCount(eSpec, iToAssign)
