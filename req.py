import requests
from requests.auth import HTTPBasicAuth

def check_server_status(url) : 
    # print("Check url : " + url)
    try :
        response = requests.get(url, timeout=1)
        if response.status_code == 200 : 
            return True
        
        else :
            return False
    except requests.RequestException : 
        return False
    
