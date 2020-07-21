import json
import pytest

from aws_cdk import core
from sagemaker-cdk.sagemaker_cdk_stack import SagemakerCdkStack


def get_template():
    app = core.App()
    SagemakerCdkStack(app, "sagemaker-cdk")
    return json.dumps(app.synth().get_stack("sagemaker-cdk").template)


def test_sqs_queue_created():
    assert("AWS::SQS::Queue" in get_template())


def test_sns_topic_created():
    assert("AWS::SNS::Topic" in get_template())
