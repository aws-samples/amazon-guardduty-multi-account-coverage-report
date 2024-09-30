""" using AwsIterator, paginates GuardDuty ListCoverage.
Creates a CSV report with columns for Account, Region, ResourceType, CoverageStatus, Issue.
If an account/region has no coverage, a single like is added noting no coverage
Example Output:


Account,Region,ResourceId,ResourceType,CoverageStatus,Issue
111111111111,us-east-1,arn:aws:ec2:us-east-1:111111111111:instance/i-xxxxxxxxxxxxxxxx,EC2,UNHEALTHY,No Agent Reporting
222222222222,us-east-1,No Coverage Detected
111111111111,us-east-2,No Coverage Detected
222222222222,us-east-2,No Coverage Detected



The script by default will evaluate all accounts and regions.  you must provide the name of an IAM role within each member account that will be assumed.
"""

import argparse
from iterate import AwsIterator
import csv
import json


arg_parser = argparse.ArgumentParser(description='Run GuardDuty Coverage Report')
arg_parser.add_argument('--role-name', required=True, default='GuardDutyCoverageRole', help='Name of IAM role to assume in each account. This role must already exsist.')
arg_parser.add_argument('--all-accounts', action='store_true', help='Run over all AWS Acccounts within Organzation.  Requires permission to make AWS Organziation API calls.')
arg_parser.add_argument('--all-regions', action='store_true', help='Iterate over all AWS regions')
arg_parser.add_argument('--account-ids', type=str, default=None, help='Comma separated list of account IDs to iterate over.')
arg_parser.add_argument('--ous', type=str, default=None, help='Comma separated list of OUs to run against.  You can also specify a root id.')
arg_parser.add_argument('--regions', type=str, default=None, help='Comma separated list of regions to iterate over')

args = arg_parser.parse_args()
if args.all_accounts is False and args.account_ids is None and args.ous is None:
    print("You must specify either --all-accounts, --account-ids, or --ous")
    exit(1)
if args.all_regions is None and args.regions is None:
    print("You must specify either --all-regions or --regions")
    exit(1)
    
def guard_duty_coverage(boto_session, account_id, region, payload):
    response = {
        'account_id': account_id,
        'region': region
    }
    try:
        gd_client = boto_session.client('guardduty')
        detector_id = gd_client.list_detectors().get('DetectorIds')[0]
        list_coverage_paginator = gd_client.get_paginator('list_coverage')
        result = list_coverage_paginator.paginate(
            DetectorId=detector_id).build_full_result()
        response['response'] = result.get('Resources', [])
    except botocore.exceptions.ClientError as error:
        response['response'] = [
            {
                "Error": str(error)
            }
        ]
    return response

def build_report_row(account_id, region, gd_result):
    if 'Error' in gd_result:
        return [account_id, region, gd_result.get('Error')]
    gd_item = [account_id, region]
    gd_item.append(gd_result.get('ResourceId'))
    gd_item.append(gd_result.get('ResourceDetails').get('ResourceType'))
    gd_item.append(gd_result.get('CoverageStatus'))
    gd_item.append(gd_result.get('Issue', 'N.A'))
    return gd_item

iterator = AwsIterator(member_account_role_name=args.role_name)
if args.all_accounts:
    iterator.all_accounts()
else:
    if args.account_ids :
        iterator.add_accounts(type='accounts', values = args.account_ids.split(','))
    elif args.ous:
        iterator.add_accounts(type='ous', values = args.ous.split(','))
if args.all_regions:
    iterator.all_regions()
else:
    iterator.add_regions(args.regions.split(','))

all_gd_results = iterator.iterate(guard_duty_coverage)
print ("writing results to ./report.csv")
with open ('report.csv', 'w') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Account', 'Region', 'ResourceId', 'ResourceType', 'CoverageStatus', 'Issue'])
    for account_id, regions_data in all_gd_results.items():
        for region, gd_results in regions_data.items():
            if len(gd_results) == 0:
                writer.writerow([account_id, region, 'No Coverage Detected'])
            else:
                for gd_result in gd_results:
                    writer.writerow(build_report_row(account_id, region, gd_result))