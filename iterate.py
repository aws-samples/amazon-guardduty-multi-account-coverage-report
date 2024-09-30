"""The AwsIterator class provides an easy way to execute a specific python script against any number of accounts and regions.

You can specify either a list of account(s) or Ou(s) or specify all account.

You can specify a list of regions or specify all regions are in scope.

when you call iterator, assume role to an existing IAM role in that account and creates a boto3 session.  The script must accept
a pararmeter named boto_session and create any client/resources using this session.  Results are returned as a dictionary.  The first
level is by account, then region.

{
    "111111111111": {
        "us-east-1": [
            "results from script"
        ],
        "us-west-2": [
            "results from script"
        ]
    }
}


"""

import boto3
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

MAX_WORKERS = 10

class AccountType(Enum):
    accounts='accounts'
    ous='ou'
    org='org'

sts_client = boto3.client('sts')

class AwsIterator:
    """ Specific accounts and regions that should be iterated over.
    
    Provides an easy way to list accounts, OUs/org, and regions that you need to do something.
    This handles assuming a role and running a provided function in each account/region concurrently"""
    
    def __init__(self, region_name:str = 'us-east-1',member_account_role_name:str = None):
        self.org_client = boto3.client(
            'organizations',
            region_name=region_name)
        self.member_account_role_name = member_account_role_name
        self.list_accounts_for_parent = self._list_accounts_for_parent
        self.accounts = set()
        self.regions = set()
    def all_accounts(self):
        root_id = self.org_client.list_roots().get('Roots')[0].get('Id')
        self.add_accounts(type='ou', value = root_id)

    def all_regions(self, opt_in_status:list = None):
        if opt_in_status is not None:
            payload = {'Filters': [{'Key': 'opt-in-status', 'Values': opt_in_status}]}
        else:
            payload = {}
        all_regions = list(
            map(
                lambda r: r['RegionName'],
                boto3.client(
                    'ec2').describe_regions(**payload).get(
                        'Regions', []
                    )
                )
            )
        self.regions.update(all_regions)
    def iterate(self, function:callable = None, payload = None):
        print ("Start Iterate")
        response = {}
        futures = []
        for account_id in self.accounts:
            response[account_id] = {}            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                for region in self.regions:
                    payload = {
                        "boto_session": deepcopy(self._build_session(
                            account_id, region)),
                        "payload": payload,
                        "account_id": account_id,
                        "region": region
                        }
                    futures.append(executor.submit(function, **payload))
        for future in as_completed(futures):
            try:
                result = future.result()
                response[result['account_id']][result['region']] = result.get('response')
            except Exception as error:
                print (f"future error: {error}")
        return response

    def _build_session(self, account_id, region):
        credentials = sts_client.assume_role(            
            RoleArn=f"arn:aws:iam::{account_id}:role/{self.member_account_role_name}",
            RoleSessionName="CrossAccountRole"
        )
        #create a boto3 session using the above credentials, scope to region
        return boto3.Session(
            aws_access_key_id=credentials.get('Credentials')['AccessKeyId'],
            aws_secret_access_key=credentials.get('Credentials')['SecretAccessKey'],
            aws_session_token=credentials.get('Credentials')['SessionToken'],
            region_name=region
        )

    def add_accounts(self, type:AccountType = None, value:str = None, values:list = None):
        if values is None:
            values = list()
        if not value is None:
            values.append(value)
        {
            'accounts': self._add_accounts,
            'ou': self._add_ous
        }.get(type)(values=values)

    def _add_accounts(self, values:list = None):
        self.accounts.update(set(values))

    def _add_ous(self, values:list = None):
        for ou_id in values:
            accounts = list(
                map(
                    lambda a: a.get('Id', None),
                    self.list_accounts_for_parent(ParentId=ou_id)
                    )
                )
            self.add_accounts(
                type='accounts',
                values=accounts)

            ou_id = list(
                map(
                    lambda a: a.get('Id', None),
                    self._list_organizational_units_for_parent(ParentId=ou_id)
                    )
                )
            self.add_accounts(
                type='ou',
                values=ou_id)
        pass


    def _list_accounts_for_parent(self, ParentId:str = None):
        return self.org_client.get_paginator(
            'list_accounts_for_parent').paginate(
                ParentId=ParentId).build_full_result().get(
                    'Accounts', [])

    def _list_organizational_units_for_parent(self, ParentId:str = None):
        return self.org_client.get_paginator(
            'list_organizational_units_for_parent').paginate(
                ParentId=ParentId).build_full_result().get(
                    'OrganizationalUnits', [])

    def add_regions(self, regions:list = None):
        self.regions.update(set(regions))
