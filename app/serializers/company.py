from rest_framework import serializers
import re


class CompanyDetailsSerializer(serializers.Serializer):
    ownerID = serializers.CharField(required=True)
    companyname = serializers.CharField(required=True)
    defaultDenom = serializers.CharField(required=True)
    handle = serializers.CharField(required=True)

    def validate(self, attrs):
        super().validate(attrs)
        return {
            "ownerID": attrs["ownerID"],
            "accountType": "BUSINESS",
            "accountName": attrs["companyname"],
            "accountHandle": attrs["handle"],
            "defaultDenom": attrs["defaultDenom"],
        }
