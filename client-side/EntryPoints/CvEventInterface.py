# CvEventInterface.py
# Entry point module for Civilization IV Python Event System

import sys

try:
    import CustomCiv4EventHandler 
except ImportError:
    try:
        import CustomCiv4EventHandler
    except ImportError:
        import CvEventManager
        CustomCiv4EventHandler = None

# Instantiate event manager safely
if CustomCiv4EventHandler and hasattr(CustomCiv4EventHandler, 'CustomCiv4EventHandler'):
    normalEventManager = CustomCiv4EventHandler.CustomCiv4EventHandler()
else:
    normalEventManager = CvEventManager.CvEventManager()

def getEventManager():
    """Returns the active event manager instance to the Civ IV engine."""
    return normalEventManager

def onEvent(argsList):
    """
    Delegates incoming game engine events to the event manager.
    Supports both onEvent and handleEvent method signatures.
    """
    em = getEventManager()
    if hasattr(em, 'onEvent'):
        return em.onEvent(argsList)
    elif hasattr(em, 'handleEvent'):
        return em.handleEvent(argsList)
    return False
