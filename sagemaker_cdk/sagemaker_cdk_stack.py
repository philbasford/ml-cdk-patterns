from aws_cdk import (
    # aws_iam as iam,
    # aws_sns as sns,
    # aws_sns_subscriptions as subs,
    aws_applicationautoscaling as asg,
    aws_ec2 as ec2,
    aws_sagemaker as sagemaker,
    core
)

MODEL = 's3://sagemaker-eu-west-1-893147475170/sagemaker/DEMO-xgboost-byo/DEMO-local-xgboost-model/model.tar.gz'
#XGBOOST = '433757028032.dkr.ecr.us-west-2.amazonaws.com/xgboost:1'
XGBOOST = '141502667606.dkr.ecr.eu-west-1.amazonaws.com/sagemaker-xgboost:0.90-2-cpu-py3'
#XGBOOST = '14141502667606.dkr.ecr.eu-west-1.amazonaws.com/sagemaker-xgboost:1'
ROLE = 'arn:aws:iam::893147475170:role/service-role/AmazonSageMaker-ExecutionRole-20200620T212968'


def base_vpc(stack):

    vpc = ec2.Vpc(
        stack, "SageMakerVpc",
        cidr='10.0.0.0/21',
        max_azs=3,
        subnet_configuration=[
            ec2.SubnetConfiguration(
                name="Ingress", subnet_type=ec2.SubnetType.PUBLIC,
                cidr_mask=24, reserved=False),
            ec2.SubnetConfiguration(
                name="Application", subnet_type=ec2.SubnetType.PRIVATE,
                cidr_mask=24, reserved=False),
            ec2.SubnetConfiguration(
                name="Data", subnet_type=ec2.SubnetType.ISOLATED,
                cidr_mask=24, reserved=True)
        ]
    )

    vpc.add_gateway_endpoint(
        'DynamoDbEndpoint',
        service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
    )

    vpc.add_gateway_endpoint(
        'S3Endpoint',
        service=ec2.GatewayVpcEndpointAwsService.S3,
    )

    vpc.add_interface_endpoint(
        "SageMakerEndpoint",
        service=ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_RUNTIME
    )

    return vpc


def base_model(stack, vpc):

    primary_container = {
        "modelDataUrl":  MODEL,
        "image": XGBOOST
    }

    selection = ec2.SubnetSelection(
        subnet_type=ec2.SubnetType.PRIVATE,
        one_per_az=True
    )

    sg = ec2.SecurityGroup(
        stack,
        "SageMakerSecurityGroup",
        vpc=vpc
    )

    sagemaker.CfnModel(
        stack, "SageMakerModel",
        execution_role_arn=ROLE,
        primary_container=primary_container,
        vpc_config=sagemaker.CfnModel.VpcConfigProperty(
            security_group_ids=[sg.security_group_id],
            subnets=[
                vpc.private_subnets[0].subnet_id, 
                vpc.private_subnets[1].subnet_id
            ]
        )
    )

    model_name = core.Fn.get_att("SageMakerModel", "ModelName").to_string()

    production_variants = [{
        "modelName": model_name,
        "variantName": "AllTraffic",
        "initialInstanceCount": 1,
        "instanceType": "ml.m5.large",
        "initialVariantWeight": 2
    }]

    sagemaker.CfnEndpointConfig(
        stack, "SageMakerEndpointConf",
        production_variants=production_variants
    )

    endpoint = sagemaker.CfnEndpoint(
        stack, "SageMakerEndpoint",
        endpoint_config_name=core.Fn.get_att(
            "SageMakerEndpointConf",
            "EndpointConfigName"
        ).to_string()
    )

    endpoint_name = core.Fn.get_att("SageMakerEndpoint", "EndpointName").to_string()

    target = asg.ScalableTarget(
        stack, "ScalableTarget",
        service_namespace=asg.ServiceNamespace.SAGEMAKER,
        max_capacity=4,
        min_capacity=2,
        resource_id=f"endpoint/{endpoint_name}/variant/AllTraffic",
        scalable_dimension="sagemaker:variant:DesiredInstanceCount"
    )

    asg.TargetTrackingScalingPolicy(
        stack, "ScalablePolicy",
        scaling_target=target,
        target_value=30000,
        scale_in_cooldown=core.Duration.seconds(300),
        scale_out_cooldown=core.Duration.seconds(300),
        predefined_metric=asg.PredefinedMetric.SAGEMAKER_VARIANT_INVOCATIONS_PER_INSTANCE
    )

    core.Dependency(source=endpoint, target = target)

class SagemakerCdkStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = base_vpc(self)
        base_model(self, vpc)
