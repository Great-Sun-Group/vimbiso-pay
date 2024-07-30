from rest_framework import serializers 
import json, os, requests, re
from decouple import config

from bot.utils import convert_timestamp_to_date

class OfferCredexSerializer(serializers.Serializer):
    authorizer_member_id = serializers.CharField(required=True)
    issuer_member_id = serializers.CharField(required=True)
    handle = serializers.CharField(required=True)
    amount = serializers.FloatField(required=True)
    dueDate = serializers.FloatField(required=True)
    currency = serializers.CharField(required=True)
    securedCredex = serializers.BooleanField(required=True)

    def validate(self, attrs):
        attrs['full_name'] = f"{attrs.get('first_name')} {attrs.get('last_name')}"
        if not re.match(r'(?i)(?:[a-zA-Z])+(?:\s[a-zA-Z]+)*(?:\s[a-zA-Z]+)?$', attrs.get('full_name')):
            raise serializers.ValidationError({"full_name": "Invalid name(s)"})
        

        url = f"{config('CREDEX')}/getAccountByHandle"

        payload = json.dumps({
            "accountHandle": attrs.get('handle')
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'x-api-key': config('CREDEX_API_CREDENTIALS'),
        }
        print(headers)
        print(payload)
        response = requests.request("GET", url, headers=headers, data=payload)
        print(response.content)
        try:
            if response.status_code == 200:
                data = response.json()
                if not data.get('Error'):
                    data = data['accountData']
                    return {
                        "issuerAccountID": attrs.get('authorizer_member_id'),
                        "memberID": attrs.get('issuer_member_id'),
                        "receiverAccountID": data['accountID'],
                        "Denomination": attrs.get('currency'),
                        "InitialAmount": attrs.get('amount'),
                        "dueDate": convert_timestamp_to_date(attrs.get('dueDate')),
                        "securedCredex": attrs.get('securedCredex'),
                        "handle": attrs.get('handle'),
                        "full_name": f"{data.get('accountName')}"
                    }
            print("EROR : ", response.content)
        except Exception as e:
            print("EROR : ", response.content, e)
            pass
            
        raise serializers.ValidationError({"recipient": "Handle Not Found"})
        



