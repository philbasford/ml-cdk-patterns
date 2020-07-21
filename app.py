#!/usr/bin/env python3

from aws_cdk import core

from sagemaker_cdk.sagemaker_cdk_stack import SagemakerCdkStack


app = core.App()
SagemakerCdkStack(app, "sagemaker-cdk", env={'region': 'us-west-2'})

app.synth()
