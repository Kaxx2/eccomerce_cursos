import requests

url = "https://TU_SAP_SERVER:50000/b1s/v1/Login"

payload = {
    "CompanyDB": "TU_BASE",
    "UserName": "TU_USER",
    "Password": "TU_PASSWORD"
}

response = requests.post(url, json=payload, verify=False)

print("STATUS LOGIN:", response.status_code)

cookies = response.cookies