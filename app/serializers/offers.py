from rest_framework import serializers
import json, os, requests, re
from decouple import config

from core.utils.utils import convert_timestamp_to_date


class OfferCredexSerializer(serializers.Serializer):
    authorizer_member_id = serializers.CharField(required=True)
    issuer_member_id = serializers.CharField(required=True)
    handle = serializers.CharField(required=True)
    amount = serializers.FloatField(required=True)
    dueDate = serializers.FloatField(required=True)
    currency = serializers.CharField(required=True)
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
            # {
            #     'message': 'Account found successfully',
            #     'data': {
            #         'action': {
            #             'id': '001ae1dc-6c4d-4e8f-b50a-bd3793727341',
            #             'type': 'ACCOUNT_FOUND',
            #             'timestamp': '2024-11-21T05:03:33.388Z',
            #             'actor': 'system',
            #             'details': {
            #                 'accountID': '001ae1dc-6c4d-4e8f-b50a-bd3793727341',
            #                 'accountName': 'Garnet Sharara Personal',
            #                 'accountHandle': '263782624032',
            #                 'defaultDenom': 'USD'
            #             }
            #         },
            #         'dashboard': {}
            #     }
            # }
            try:
                if success:
                    if data.get("message") == "Account found successfully":
                        data = data.get("data").get("action").get("details")
                        return {
                            "issuerAccountID": attrs.get("authorizer_member_id"),
                            "memberID": attrs.get("issuer_member_id"),
                            "receiverAccountID": data["accountID"],
                            "Denomination": attrs.get("currency"),
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
