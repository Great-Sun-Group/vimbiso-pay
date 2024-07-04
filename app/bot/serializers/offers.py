from rest_framework import serializers 
import json, os, requests, re

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
        
        # phone_number = attrs.get('recipient_phone_number').replace("+", "")
        # if not phone_number.isdigit():
        #     raise serializers.ValidationError({"recipient_phone_number": "Invalid phone number"})

        url = f"{os.getenv('CREDEX')}/getMemberByHandle"

        payload = json.dumps({
            "handle": attrs.get('handle')
        })
        headers = {
            'X-Github-Token': os.getenv('CREDEX_API_CREDENTIALS'),
            'Content-Type': 'application/json',
            'API-KEY': os.getenv('CREDEX_API_CREDENTIALS'),
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        try:
            if response.status_code == 200:
                data = response.json()
                if not data.get('Error'):
                    data = data['memberData']
                    return {
                        "authorizerMemberID": attrs.get('authorizer_member_id'),
                        "issuerMemberID": attrs.get('issuer_member_id'),
                        "receiverMemberID": data['memberID'],
                        "Denomination": attrs.get('currency'),
                        "InitialAmount": attrs.get('amount'),
                        "dueDate": convert_timestamp_to_date(attrs.get('dueDate')),
                        "securedCredex": attrs.get('securedCredex'),
                        "handle": attrs.get('handle'),
                        "full_name": f"{data.get('displayName')}"
                    }
            print("EROR : ", response.content)
        except Exception as e:
            print("EROR : ", response.content, e)
            pass
            
        raise serializers.ValidationError({"recipient": "Handle Not Found"})
        



