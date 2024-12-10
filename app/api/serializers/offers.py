import re

from core.utils.utils import convert_timestamp_to_date
from rest_framework import serializers


class OfferCredexSerializer(serializers.Serializer):
    authorizer_member_id = serializers.CharField(required=True)
    issuer_member_id = serializers.CharField(required=True)
    handle = serializers.CharField(required=True)
    amount = serializers.FloatField(required=True)
    dueDate = serializers.FloatField(required=True)
    denomination = serializers.CharField(required=True)
    securedCredex = serializers.BooleanField(required=True)

    def validate(self, attrs):
        attrs["full_name"] = f"{attrs.get('first_name')} {attrs.get('last_name')}"
        if not re.match(
            r"(?i)(?:[a-zA-Z])+(?:\s[a-zA-Z]+)*(?:\s[a-zA-Z]+)?$",
            attrs.get("full_name"),
        ):
            raise serializers.ValidationError({"full_name": "Invalid name(s)"})

        if self.context.get("api_interactions"):
            print("API INTERACTIONS")
            success, data = self.context["api_interactions"].validate_handle(
                attrs.get("handle").lower()
            )
            print(success, data)
            try:
                if success:
                    if data.get("message") == "Account found successfully":
                        data = data.get("data").get("action").get("details")
                        return {
                            "issuerAccountID": attrs.get("authorizer_member_id"),
                            "memberID": attrs.get("issuer_member_id"),
                            "receiverAccountID": data["accountID"],
                            "Denomination": attrs.get("denomination"),
                            "InitialAmount": attrs.get("amount"),
                            "dueDate": convert_timestamp_to_date(attrs.get("dueDate")),
                            "securedCredex": attrs.get("securedCredex"),
                            "handle": attrs.get("handle").lower(),
                            "full_name": f"{data.get('accountName')}",
                            "OFFERSorREQUESTS": "OFFERS",
                            "credexType": "PURCHASE",
                        }
            except Exception as e:
                print(e)

        raise serializers.ValidationError({"recipient": "Recipient Account Not Found"})
