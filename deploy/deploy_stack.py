import os
import sys
from string import Template

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

        self.config = config

        """
        Set up domain and subdomain variables
        Along with aliases used within CloudFront
        """
        self.domain = self.config.get("domain")
        self.sub_domain = ".".join([self.config.get("subdomain"), self.domain])
        self.zone = self.get_zone()

        self.certificate = self.get_certificate()

        self.bucket_assets = self.create_asset_bucket()
        self.site_distribution = self.create_site_distribution()

        if self.config.get("redirect_apex", True):
            self.bucket_redirect = self.create_redirect_bucket()
            self.redirect_distribution = self.create_redirect_distribution()

        self.create_records()

    def get_zone(self):
        return route53.HostedZone.from_lookup(
            self,
            self.config.get("stack_name") + "_zone",
            domain_name=self.config.get("domain")
        )

    def get_pricing_class(self):
        """
        Set the price class for CloudFront
        """
        price_class_dict = {
            "100": cloudfront.PriceClass.PRICE_CLASS_100,   # US, Canada, and Europe
            "200": cloudfront.PriceClass.PRICE_CLASS_200,   # US, Canada, Europe, Asia, Middle East, and Africa
            "ALL": cloudfront.PriceClass.PRICE_CLASS_ALL    # All Edge locations
        }
        return price_class_dict.get(self.config.get("price_class", "100"))

    def get_certificate(self):
        """
        Get existing ACM certificate
        """
        acm_arn_template = Template("arn:aws:acm:us-east-1:$account:certificate/$certificate_id")
        if self.config.get("acm_id"):
            arn = acm_arn_template.substitute(
                account=os.getenv("CDK_DEFAULT_ACCOUNT"),
                certificate_id=self.config.get("acm_id")
            )
            return certificatemanager.Certificate.from_certificate_arn(
                self,
                self.config.get("stack_name") + "_cert",
                arn
            )
        else:
            print("Certificate creation not yet supported by this script")
            sys.exit(1)

    def create_asset_bucket(self):
        """
        Create S3 Bucket for assets"
        """
        return s3.Bucket(
            self,
            self.config.get("stack_name") + "_s3",
            removal_policy=core.RemovalPolicy.DESTROY
        )

    def create_redirect_bucket(self):
        return s3.Bucket(
            self,
            self.config.get("stack_name") + "_redirect",
            website_redirect={"host_name": self.sub_domain,
                              "protocol": s3.RedirectProtocol.HTTPS},
            removal_policy=core.RemovalPolicy.DESTROY,
            public_read_access=True
        )

    def gather_assets(self):
        """
        Gather assets and deploy them to the S3 bucket
        Assumes path is <pwd>/../<config_source>
        """
        paths = [ os.path.join(os.getcwd(), self.config.get("source")),
                  os.path.join(os.getcwd(), "..", self.config.get("source")) ]
        assets_path = [ path for path in paths if os.path.isdir(path) ]
        if assets_path:
            return assets_path.pop()

    def create_bucket_deployment(self):
        assets_directory = self.gather_assets()
        return s3deploy.BucketDeployment(
            self,
            self.config.get("stack_name") + "_deploy",
            sources=[s3deploy.Source.asset(assets_directory)],
            destination_bucket=self.bucket_assets,
        )

    def create_asset_oai_config(self):
        """
        Create OAI policy for S3/CloudFront
        Means bucket does not need to be public
        """
        s3_oai = cloudfront.OriginAccessIdentity(
            self,
            self.config.get("stack_name") + "_OAI"
        )
        return cloudfront.S3OriginConfig(
            s3_bucket_source=self.bucket_assets,
            origin_access_identity=s3_oai
        )

    def create_redirect_oai_config(self):
        # Workaround for known bug with CloudFront and S3 Redirects
        # https://github.com/aws/aws-cdk/issues/5700
        return cloudfront.CustomOriginConfig(
            domain_name=self.bucket_redirect.bucket_website_domain_name,
            origin_protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY
        )

    def create_site_distribution(self):
        """
        Pull it all together in a CloudFront distribution
        """
        return cloudfront.CloudFrontWebDistribution(
            self, 
            self.config.get("stack_name") + "_cloudfront",
            origin_configs=[
                cloudfront.SourceConfiguration(
                    s3_origin_source=self.create_asset_oai_config(),
                    behaviors=[
                        cloudfront.Behavior(is_default_behavior=True)
                    ]
                )
            ],
            viewer_certificate=cloudfront.ViewerCertificate.from_acm_certificate(
                self.certificate,
                aliases=[self.sub_domain],
                security_policy=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2018,
                ssl_method=cloudfront.SSLMethod.SNI
            ),
            price_class=self.get_pricing_class()
        )

    def create_redirect_distribution(self):
        return cloudfront.CloudFrontWebDistribution(
            self, 
            self.config.get("stack_name") + "_cloudfront_redirect",
            origin_configs=[
                cloudfront.SourceConfiguration(
                    custom_origin_source=self.create_redirect_oai_config(),
                    behaviors=[
                        cloudfront.Behavior(is_default_behavior=True)
                    ]
                )
            ],
            viewer_certificate=cloudfront.ViewerCertificate.from_acm_certificate(
                self.certificate,
                aliases=[self.domain],
                security_policy=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2018,
                ssl_method=cloudfront.SSLMethod.SNI
            ),
            price_class=self.get_pricing_class()
        )

    def create_records(self):
        """
        Setup route53 entries
        At a minimum:
          A Record: subdomain.example.com
        Optional:
          A Record: example.com
          AAAA Record: example.com
          AAAA Record: subdomain.example.com
        """
        self.cloudfront_site_target = route53.RecordTarget.from_alias(
            route53_targets.CloudFrontTarget(
                self.site_distribution
            )
        )
        if self.config.get("redirect_apex", True):
            apex_target = route53.RecordTarget.from_alias(
                route53_targets.CloudFrontTarget(
                    self.redirect_distribution
                )
            )
        else:
            apex_target = self.cloudfront_site_target

        self.create_site_records()
        self.create_apex_records(apex_target)

    def create_site_records(self):
        route53.ARecord(
            self,
            self.config.get("stack_name") + "_v4_sub_alias",
            zone=self.zone,
            record_name=self.config.get("subdomain"),
            target=self.cloudfront_site_target
        )

        if self.config.get("ipv6_support", False):
            route53.AaaaRecord(
                self,
                self.config.get("stack_name") + "_v6_sub_alias",
                zone=self.zone,
                record_name=self.config.get("subdomain"),
                target=self.cloudfront_site_target
            )

    def create_apex_records(self, apex_target):
        route53.ARecord(
            self,
            self.config.get("stack_name") + "_v4_apex_alias",
            zone=self.zone,
            target=apex_target
        )

        if self.config.get("ipv6_support", False):
            route53.AaaaRecord(
                self,
                self.config.get("stack_name") + "_v6_apex_alias",
                zone=self.zone,
                target=apex_target
            )
