import httplib
import simplejson as json

# 1. Initialize connection to localhost on port 800
conn = httplib.HTTPConnection("localhost", 8000)

try:
    # 2. Send GET request to '/api/data'
    conn.request("GET", "/api")
    
    # 3. Retrieve HTTP response
    response = conn.getresponse()
    
    # 4. Check if the response status is 200 OK
    if response.status == httplib.OK:  # httplib.OK is the constant for status 200
        # Read the raw JSON string from the response
        raw_data = response.read()
        
        # 5. Deserialize the JSON string into a Python object (dictionary/list)
        data_obj = json.loads(raw_data)
        
        print "Status:", response.status, response.reason
        print "Deserialized JSON object:", data_obj
    else:
        print "Failed with status:", response.status, response.reason

finally:
    # Always close the connection when done
    conn.close()
