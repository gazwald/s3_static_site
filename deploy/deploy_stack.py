import os

from aws_cdk import core
import aws_cdk.aws_certificatemanager as certificatemanager
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3deploy
import aws_cdk.aws_cloudfront as cloudfront


class DeployStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        domain = os.getenv('DOMAIN', 'gazwald.com')
        sub_domain = "mel." + domain

        """
        Get existing ACM certificate
        """
        certificate_id = '92fca839-f71e-41ce-bfe0-458a09ae60e9'
        arn = 'arn:aws:acm:us-east-1:{account}:certificate/{certificate_id}'.format(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
                                                                                    certificate_id=certificate_id)
        certificate = certificatemanager.Certificate.from_certificate_arn(self, "mel_gazwald_cert", arn)

        """
        Create S3 Bucket for assets"
        """
        s3_bucket_source = s3.Bucket(self, "mel_gazwald_s3", removal_policy=core.RemovalPolicy.DESTROY)

        """
        Gather assets and deploy them to the S3 bucket
        Assumes path, relative to this directory, is ../src
        """
        assets_directory = os.path.join(os.getcwd(), '..', 'src')
        s3deploy.BucketDeployment(self, "mel_gazwald_deploy",
            sources=[s3deploy.Source.asset(assets_directory)],
            destination_bucket=s3_bucket_source,
        )

        """
        Create OAI policy for S3/CloudFront
        Means bucket does not need to be public
        """
        s3_origin_config = cloudfront.S3OriginConfig(s3_bucket_source=s3_bucket_source,
                                                     origin_access_identity=cloudfront.OriginAccessIdentity(self, "mel_gazwald_OAI"))

        """
        Pull it all together in a CloudFront distribution
        """
        distribution = cloudfront.CloudFrontWebDistribution(self, "mel_gazwald_cloudfront",
            origin_configs=[cloudfront.SourceConfiguration(
                s3_origin_source=s3_origin_config,
                behaviors=[cloudfront.Behavior(is_default_behavior=True)]
            )],
            viewer_certificate=cloudfront.ViewerCertificate.from_acm_certificate(certificate,
                aliases=[sub_domain],
                security_policy=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2018,
                ssl_method=cloudfront.SSLMethod.SNI
            )
        )
