from rest_framework import serializers
import re

class MemberDetailsSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    currency = serializers.CharField(required=True)
    email = serializers.CharField(required=True)


    def validate(self, attrs):
        attrs['full_name'] = f"{attrs.get('first_name')} {attrs.get('last_name')}"
        if not re.match(r'(?i)(?:[a-zA-Z])+(?:\s[a-zA-Z]+)*(?:\s[a-zA-Z]+)?$', attrs.get('full_name')):
            raise serializers.ValidationError({"full_name": "Invalid name(s)"})
        
        phone_number = attrs.get('phone_number').replace("+", "")
        if not phone_number.isdigit():
            raise serializers.ValidationError({"phone_number": "Invalid phone number"})
        return {
            # "memberType": "HUMAN",
            "defaultDenom": attrs.get('currency'),
            "phone": attrs.get('phone_number'),
            "firstname": attrs.get('first_name'),
            "lastname": attrs.get('last_name'),
            "memberHandle": attrs.get('email')
        }



