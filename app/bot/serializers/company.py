from rest_framework import serializers
import re


class CompanyDetailsSerializer(serializers.Serializer):
    ownerID = serializers.CharField(required=True)
    companyname = serializers.CharField(required=True)
    defaultDenom = serializers.CharField(required=True)
    handle = serializers.CharField(required=True)

