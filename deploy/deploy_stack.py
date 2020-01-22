import os
import sys

from aws_cdk import core
import aws_cdk.aws_certificatemanager as certificatemanager
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3deploy
import aws_cdk.aws_cloudfront as cloudfront
import aws_cdk.aws_route53 as route53
import aws_cdk.aws_route53_targets as route53_targets

# TODO: Split site and redirect components

class DeployStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, config: dict,  **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        """
        Set up domain and subdomain variables
        Along with aliases used within CloudFront
        """
        domain = config.get("domain")
        sub_domain = ".".join([config.get("subdomain"), domain])

        """
        Set the price class for CloudFront
        """
        price_class_dict = {"100": cloudfront.PriceClass.PRICE_CLASS_100,   # US, Canada, and Europe
                            "200": cloudfront.PriceClass.PRICE_CLASS_200,   # US, Canada, Europe, Asia, Middle East, and Africa
                            "ALL": cloudfront.PriceClass.PRICE_CLASS_ALL}   # All Edge locations
        price_class = price_class_dict.get(config.get("price_class", "100"))

        """
        Get existing ACM certificate
        """
        if config.get("acm_id"):
            arn = "arn:aws:acm:us-east-1:{account}:certificate/{certificate_id}".format(account=os.getenv("CDK_DEFAULT_ACCOUNT"),
                                                                                        certificate_id=config.get("acm_id"))
            certificate = certificatemanager.Certificate.from_certificate_arn(
                self,
                config.get("stack_name") + "_cert",
                arn
            )
        else:
            print("Certificate creation not yet supported by this script")
            sys.exit(1)

        """
        Create S3 Bucket for assets"
        """
        site_bucket = s3.Bucket(
            self,
            config.get("stack_name") + "_s3",
            removal_policy=core.RemovalPolicy.DESTROY
        )

        if config.get("redirect_apex", True):
            redirect_bucket = s3.Bucket(
                self,
                config.get("stack_name") + "_redirect",
                website_redirect={"host_name": sub_domain},
                removal_policy=core.RemovalPolicy.DESTROY
            )

        """
        Gather assets and deploy them to the S3 bucket
        Assumes path is <pwd>/../<config_source>
        """
        assests_path = os.path.join(os.getcwd(), "..", config.get("source"))
        if os.path.isdir(assests_path):
            assets_directory = assests_path
        else:
            print(f"Unable to find src directory: {assets_path}")
            sys.exit(1)

        s3deploy.BucketDeployment(
            self,
            config.get("stack_name") + "_deploy",
            sources=[s3deploy.Source.asset(assets_directory)],
            destination_bucket=site_bucket,
        )

        """
        Create OAI policy for S3/CloudFront
        Means bucket does not need to be public
        """
        s3_oai = cloudfront.OriginAccessIdentity(
            self,
            config.get("stack_name") + "_OAI"
        )
        s3_site_origin_config = cloudfront.S3OriginConfig(
            s3_bucket_source=site_bucket,
            origin_access_identity=s3_oai
        )

        # Workaround for known bug with CloudFront and S3 Redirects
        # https://github.com/aws/aws-cdk/issues/5700
        s3_redirect_origin_config = cloudfront.S3OriginConfig(
            domain_name=redirect_bucket.bucket_website_url,
            origin_protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY
        )

        """
        Pull it all together in a CloudFront distribution
        """

        site_distribution = cloudfront.CloudFrontWebDistribution(
            self, 
            config.get("stack_name") + "_cloudfront",
            origin_configs=[
                cloudfront.SourceConfiguration(
                    s3_origin_source=s3_site_origin_config,
                    behaviors=[cloudfront.Behavior(is_default_behavior=True)]
                )
            ],
            viewer_certificate=cloudfront.ViewerCertificate.from_acm_certificate(
                certificate,
                aliases=[sub_domain],
                security_policy=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2018,
                ssl_method=cloudfront.SSLMethod.SNI
            ),
            price_class=price_class
        )

        if config.get("redirect_apex", True):
            redirect_distribution = cloudfront.CloudFrontWebDistribution(
                self, 
                config.get("stack_name") + "_cloudfront_redirect",
                origin_configs=[
                    cloudfront.SourceConfiguration(
                        s3_origin_source=s3_redirect_origin_config,
                        behaviors=[cloudfront.Behavior(is_default_behavior=True)]
                    )
                ],
                viewer_certificate=cloudfront.ViewerCertificate.from_acm_certificate(
                    certificate,
                    aliases=[domain],
                    security_policy=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2018,
                    ssl_method=cloudfront.SSLMethod.SNI
                ),
                price_class=price_class
            )

        """
        Setup route53 entries
        At a minimum:
          A Record: subdomain.example.com
        Optional:
          A Record: example.com
          AAAA Record: example.com
          AAAA Record: subdomain.example.com
        """
        zone = route53.HostedZone.from_lookup(
            self,
            config.get("stack_name") + "_zone",
            domain_name=config.get("domain")
        )

        cloudfront_site_target = route53.RecordTarget.from_alias(route53_targets.CloudFrontTarget(site_distribution))

        if config.get("redirect_apex", True):
            cloudfront_redirect_target = route53.RecordTarget.from_alias(route53_targets.CloudFrontTarget(redirect_distribution))
            apex_target = cloudfront_redirect_target
        else:
            apex_target = cloudfront_site_target

        route53.ARecord(
            self,
            config.get("stack_name") + "_v4_sub_alias",
            zone=zone,
            record_name=config.get("subdomain"),
            target=cloudfront_site_target
        )

        if config.get("include_apex", False):
            route53.ARecord(
                self,
                config.get("stack_name") + "_v4_apex_alias",
                zone=zone,
                target=apex_target
            )


        if config.get("ipv6_support", False):
            route53.AaaaRecord(
                self,
                config.get("stack_name") + "_v6_sub_alias",
                zone=zone,
                record_name=config.get("subdomain"),
                target=cloudfront_site_target
            )

            if config.get("include_apex", False):
                route53.AaaaRecord(
                    self,
                    config.get("stack_name") + "_v6_apex_alias",
                    zone=zone,
                    target=apex_target
                )
