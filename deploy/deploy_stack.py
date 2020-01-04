import os

from aws_cdk import core
import aws_cdk.aws_certificatemanager as certificatemanager
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3deploy
import aws_cdk.aws_cloudfront as cloudfront


class DeployStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, config: dict,  **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        domain = config.get("domain", 'gazwald.com')
        sub_domain = '.'.join(config.get("subdomain"), domain)

        """
        Get existing ACM certificate
        """
        if config.get('acm_id'):
            arn = 'arn:aws:acm:us-east-1:{account}:certificate/{certificate_id}'.format(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
                                                                                        certificate_id=config.get('acm_id'))
            certificate = certificatemanager.Certificate.from_certificate_arn(self,
                                                                              config.get('stack_name') + "_cert",
                                                                              arn)
        else:
            print("Certificate creation not yet supported")
            os.exit(1)

        """
        Create S3 Bucket for assets"
        """
        s3_bucket_source = s3.Bucket(self,
                                     config.get('stack_name') + "_s3",
                                     removal_policy=core.RemovalPolicy.DESTROY)

        """
        Gather assets and deploy them to the S3 bucket
        Assumes path, relative to this directory, is ../src
        """
        assets_directory = os.path.join(os.getcwd(), '..', 'src')
        s3deploy.BucketDeployment(self,
                                  config.get('stack_name') + '_deploy',
                                  sources=[s3deploy.Source.asset(assets_directory)],
                                  destination_bucket=s3_bucket_source,
        )

        """
        Create OAI policy for S3/CloudFront
        Means bucket does not need to be public
        """
        s3_origin_config = cloudfront.S3OriginConfig(s3_bucket_source=s3_bucket_source,
                                                     origin_access_identity=cloudfront.OriginAccessIdentity(self, config.get("stack_name") + "_OAI"))

        """
        Pull it all together in a CloudFront distribution
        """
        distribution = cloudfront.CloudFrontWebDistribution(self, 
            config.get("stack_name") + "_cloudfront",
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
