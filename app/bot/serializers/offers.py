from rest_framework import serializers
import re
import requests
from decouple import config
import json

from bot.utils import convert_timestamp_to_date

class OfferCredexSerializer(serializers.Serializer):
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
        
        # phone_number = attrs.get('recipient_phone_number').replace("+", "")
        # if not phone_number.isdigit():
        #     raise serializers.ValidationError({"recipient_phone_number": "Invalid phone number"})

        url = f"{config('CREDEX')}/getMemberByHandle"

        payload = json.dumps({
            "handle": attrs.get('handle')
        })
        headers = {
            'X-Github-Token': config('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json'
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        try:
            if response.status_code == 200:
                response = response.json()
                print(response)
                if not response.get('Error'):
                    return {
                        "issuerMemberID": attrs.get('issuer_member_id'),
                        "receiverMemberID": response['memberData']['memberID'],
                        "Denomination": attrs.get('currency'),
                        "InitialAmount": attrs.get('amount'),
                        "dueDate": convert_timestamp_to_date(attrs.get('dueDate')),
                        "securedCredex": attrs.get('securedCredex'),
                        "handle": response['memberData'].get('handle'),
                        "full_name": f"{response['memberData'].get('displayName')}"
                    }
        except Exception as e:
            pass
            
        raise serializers.ValidationError({"recipient": "Recipient Not Founs!"})
        



