import sys

try:
    import custom_civ4_event_handler_v4 as custom_civ4_event_handler
except ImportError:
    try:
        import custom_civ4_event_handler
    except ImportError:
        import CvEventManager
        custom_civ4_event_handler = None

if custom_civ4_event_handler and hasattr(custom_civ4_event_handler, 'CustomCiv4EventHandler'):
    normalEventManager = custom_civ4_event_handler.CustomCiv4EventHandler()
    print "no custom event manager"
else:
    normalEventManager = CvEventManager.CvEventManager()

if custom_civ4_event_handler:
    normalEventManager.check_http_server()

