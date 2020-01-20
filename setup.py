import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="deploy",
    version="0.0.1",

    description="An empty CDK Python app",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "deploy"},
    packages=setuptools.find_packages(where="deploy"),

    install_requires=[
        "pyyaml",
        "aws-cdk.core",
        "aws_cdk.aws_certificatemanager",
        "aws_cdk.aws_s3",
        "aws_cdk.aws_s3_deployment",
        "aws_cdk.aws_cloudfront",
        "aws_cdk.aws_route53",
        "aws_cdk.aws_route53_targets",
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
