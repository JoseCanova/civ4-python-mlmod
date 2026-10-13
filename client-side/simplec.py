import sys
import pprint
pprint.pprint(sys.path)
import simplejson as json
#import simplejson as json
#sys.path.append("./deps")  # Path to the folder containing 'simplejson'

output = json.dumps(['foo', {'bar': ('baz', None, 1.0, 2)}])
pprint.pprint(output)
def as_complex(dct):
    if '__complex__' in dct:
        return complex(dct['real'], dct['imag'])
    return dct

obj = json.loads('{"__complex__": true, "real": 1, "imag": 2}', object_hook=as_complex)
pprint.pprint(obj)

