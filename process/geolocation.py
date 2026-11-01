""" 
un programme qui  utilise une adresse IP pour demander des informations de localisation 
à un service en ligne appelé IPinfo.
 """

import requests
from requests import Response #:Une Response représente la réponse reçue du serveur après une requête.
import concurrent

def get_location(ip):
    response: Response = requests.get("https://ipinfo.io/" + ip + "/json/")
    if response.status_code == 200 :
        print(response.json())


if __name__ == "__main__":
    print(get_location('109.199.110.135'))