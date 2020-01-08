
# S3 Static Site deployed with AWS CDK


## Set up

Ensure the CDK CLI tool is present

```
$ npm install -g aws-cdk
```

Create Python virtual environment

```
$ python3 -m venv .env
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .env/bin/activate
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

## Configuration

Expected layout:

```
./config.yml  # Config, copy example_config.yml
./deploy/     # This repo
./src/        # Website code
              # Directory configurable within config.yml

By default this stack will look for `config.yml` either in the `deploy` directory or in the root path of the parent repo.

`example_config.yml` is provided as an example and should be updated for your deployment.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
