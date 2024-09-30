# GuardDuty Coverage Across Multiple Accounts/regions

This script will query up to all accounts/regions and retrieve guardduty coverage

## Requirements

* python 3.x (tested with python 3.10)
* IAM role with same name in each member account.  That can be assumed from a central account




## IAM Role

Each Member account must have an IAM role that can be assumed the account this script is run from.
The role in each member account should look like this:

### Trust Policy
```
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Principal": {
				"AWS": "arn:aws:iam::<CENTRALACCOUNTID>:root"
			},
			"Action": "sts:AssumeRole"
		}
	]
}
```
### IAM Policy
```
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"guardduty:ListCoverage",
				"guardduty:ListDetectors"
			],
			"Resource": "*"
		}
	]
}
```
If you do not already an appropiate role, you can deploy the included template [member-account-iam-role.yaml](./member-account-iam-role.yaml) as a [Service Managed StackSet](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-getting-started-create.html#stacksets-orgs-associate-stackset-with-org).  
Note: The requirement is the role this creates; this is not strictly required to deploy this via a Service Managed Stack set.

## Usage
```
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt --no-cache-dir

python3.10 guard_duty_coverage_multi_account.py --all-accounts --all-regions
```

## Help
```
myhostname % python3 guard_duty_coverage_multi_account.py --help
usage: guard_duty_coverage_multi_account.py [-h] --role-name ROLE_NAME [--all-accounts] [--all-regions] [--account-ids ACCOUNT_IDS] [--ous OUS] [--regions REGIONS]

Run GuardDuty Coverage Report

options:
  -h, --help                    show this help message and exit
  --role-name ROLE_NAME         Name of IAM role to assume in each account. This role must already exsist.
  --all-accounts                Run over all AWS Acccounts within Organzation. Requires permission to make AWS  Organziation API calls.
  --all-regions                 Iterate over all AWS regions
  --account-ids ACCOUNT_IDS     Comma separated list of account IDs to iterate over.
  --ous OUS                     Comma separated list of OUs to run against. You can also specify a root id.
  --regions REGIONS             Comma separated list of regions to iterate over
```




## Example Output
This script produced a csv report.  Below is an example of this report


|Account|Region|ResourceId|ResourceType|CoverageStatus|Issue|  
|-------|-------|-------|-------|-------|-------|  
|111111111111|us-east-1|arn:aws:ec2:us-east-1:111111111111:instance/i-xxxxxxxxxxxxxxxx|EC2|UNHEALTHY|No Agent Reporting|  
|222222222222|us-east-1|No Coverage Detected| | | |
|111111111111|us-east-2|No Coverage Detected| | | |
|222222222222|us-east-2|No Coverage Detected| | | |  